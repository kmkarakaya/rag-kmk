from rag_kmk import CONFIG
_CHROMA_PATH_OMITTED = object()
import json
import os
import time
from enum import Enum
from typing import Optional, Tuple
import logging

# Define status enum
class ChromaDBStatus(Enum):
    NEW_MEMORY = "NEW_MEMORY"
    EXISTING_PERSISTENT = "EXISTING_PERSISTENT"
    NEW_PERSISTENT = "NEW_PERSISTENT"
    MISSING_PERSISTENT = "MISSING_PERSISTENT"
    ERROR = "ERROR"

log = logging.getLogger(__name__)

# registry to map collection objects -> chromadb.Client instances
CLIENTS = {}

def get_client_for_collection(collection):
	"""
	Return the chromadb.Client instance associated with a collection, or None.
	Uses id(collection) as the key to avoid mutating collection objects.
	"""
	return CLIENTS.get(id(collection))

def _register_client_for_collection(collection, client):
	"""Internal helper to register the client for later retrieval."""
	try:
		CLIENTS[id(collection)] = client
	except Exception:
		# best-effort; ignore if cannot register
		pass

def create_chroma_client(
    collection_name: str = "default_collection",
    chromaDB_path: Optional[str] = None,
    create_new: bool = False,
    config: Optional[dict] = None,
) -> Tuple[Optional[object], ChromaDBStatus]:
    """
    Create or load a Chroma client/collection.

    Behavior:
    - chromaDB_path is None and create_new True -> create an in-memory collection (NEW_MEMORY).
    - chromaDB_path provided and exists & create_new False -> EXISTING_PERSISTENT.
    - chromaDB_path provided & create_new True -> create new persistent collection (namespaced if needed) NEW_PERSISTENT.
    - On error or chromadb not available -> (None, ERROR).
    """
    try:
        # Import ChromaDB
        try:
            import chromadb  # type: ignore
            from chromadb.config import Settings  # type: ignore
        except ImportError as e:
            log.error("Failed to import 'chromadb'. Install it with: pip install chromadb. Error: %s", e)
            return None, ChromaDBStatus.ERROR

        # Debug incoming params
        print(f"[DEBUG] create_chroma_client called with chromaDB_path={chromaDB_path!r} (type={type(chromaDB_path)}), create_new={create_new}")

        # If caller explicitly passed None as chromaDB_path and requested create_new, allow in-memory
        if chromaDB_path is None:
            if not create_new:
                log.error("chromaDB_path is None and create_new is False -> cannot proceed (explicit None means in-memory request).")
                return None, ChromaDBStatus.ERROR
            # create an in-memory client/collection
            try:
                client = chromadb.Client()  # in-memory
                collection = client.create_collection(name=collection_name)
                log.info("Created in-memory Chroma collection '%s'.", collection_name)
                return collection, ChromaDBStatus.NEW_MEMORY
            except Exception as e:
                log.error("Failed to create in-memory Chroma collection: %s", e)
                return None, ChromaDBStatus.ERROR

        # Normalize legacy folder name 'chroma_db' -> 'chromaDB' before using it on disk
        if isinstance(chromaDB_path, str):
            low = chromaDB_path.lower()
            if "chroma_db" in low:
                orig_path = chromaDB_path
                chromaDB_path = chromaDB_path.replace("chroma_db", "chromaDB").replace("chroma_db".capitalize(), "chromaDB")
                # Only log/print when a real change occurred
                if chromaDB_path != orig_path:
                    log.info("Normalized chromaDB_path from %r to %r", orig_path, chromaDB_path)
                    print(f"[INFO] Normalized chromaDB_path from {orig_path!r} to {chromaDB_path!r}")

        # Persistent path provided -> ensure directory exists
        try:
            chromaDB_path = os.path.abspath(chromaDB_path)
            os.makedirs(chromaDB_path, exist_ok=True)
            log.info("Using chromaDB persist directory (absolute): %s", chromaDB_path)
        except Exception as e:
            log.error("Failed to create/access directory '%s': %s", chromaDB_path, e)
            return None, ChromaDBStatus.ERROR

        # Initialize persistent client using chromadb.PersistentClient when available,
        # otherwise fall back to Settings(persist_directory=...) + chromadb.Client
        client = None
        try:
            # Prefer the explicit PersistentClient API if present
            if hasattr(chromadb, "PersistentClient"):
                try:
                    client = chromadb.PersistentClient(path=chromaDB_path)
                    log.info("Initialized chromadb.PersistentClient with path=%s", chromaDB_path)
                except Exception as pe:
                    log.warning("chromadb.PersistentClient(path=...) failed: %s. Falling back to Settings-based client.", pe)
                    client = None
            # Fallback: Settings + chromadb.Client
            if client is None:
                settings = Settings(persist_directory=chromaDB_path)
                client = chromadb.Client(settings)
                log.info("Initialized chromadb.Client using Settings(persist_directory=%s)", chromaDB_path)
        except Exception as e:
            log.error("Failed to initialize a persistent chromadb client for '%s'. Error: %s", chromaDB_path, e)
            return None, ChromaDBStatus.ERROR

        # At this point, we have a client (or we returned with ERROR)
        # Load existing or create depending on create_new flag
        if not create_new:
            try:
                collection = client.get_collection(name=collection_name)
                # register client (do not rely on setattr on collection)
                _register_client_for_collection(collection, client)
                # store persist path in registry via attribute on client if possible
                try:
                    setattr(client, "_persist_path", chromaDB_path)
                except Exception:
                    pass
                return collection, ChromaDBStatus.EXISTING_PERSISTENT
            except Exception as e:
                # DO NOT automatically create a new persistent collection here.
                # Instead provide robust diagnostics to the caller so they can
                # understand why the requested collection was not found.
                available_collections = []
                try:
                    # client.list_collections() exists on modern Chroma clients
                    available_collections = [c.name for c in client.list_collections()]
                except Exception:
                    try:
                        # older clients might return dicts/objects differently
                        available_collections = [getattr(c, "name", str(c)) for c in client.list_collections()]
                    except Exception:
                        available_collections = ["<unavailable>"]

                try:
                    persist_files = os.listdir(chromaDB_path)
                except Exception:
                    persist_files = ["<unreadable>"]

                log.error(
                    "Persistent collection '%s' not found in '%s'. "
                    "Available collections: %s. Persist directory contents: %s. Original error: %s",
                    collection_name, chromaDB_path, available_collections, persist_files, e
                )
                # Return a focused MISSING_PERSISTENT status so callers can act accordingly
                return None, ChromaDBStatus.MISSING_PERSISTENT

        # create_new True: avoid destructive overwrite; namespace if a same-name collection exists
        final_name = collection_name
        try:
            client.get_collection(name=collection_name)
            final_name = f"{collection_name}_{int(time.time())}"
            log.info("Collection exists; creating namespaced new collection '%s'.", final_name)
        except Exception:
            pass

        try:
            collection = client.create_collection(name=final_name)
            # register client so callers can persist after inserts
            _register_client_for_collection(collection, client)
            try:
                setattr(client, "_persist_path", chromaDB_path)
            except Exception:
                pass
            return collection, ChromaDBStatus.NEW_PERSISTENT
        except Exception as e:
            log.error("Failed to create new persistent collection '%s' at '%s': %s", final_name, chromaDB_path, e)
            return None, ChromaDBStatus.ERROR

    except Exception as e:
        log.exception("Unexpected error in create_chroma_client: %s", e)
        return None, ChromaDBStatus.ERROR


def summarize_collection(chroma_collection):
    if chroma_collection is None:
        print("No chroma collection available to summarize.")
        return json.dumps({})
    summary = {}  # Initialize summary as a dictionary
    try:
        summary["collection_name"] = getattr(chroma_collection, 'name', 'unknown')
    except Exception:
        summary["collection_name"] = 'unknown'

    # Prefer collection.count() if available
    try:
        total = chroma_collection.count()
    except Exception:
        total = 0
    summary["document_count"] = total
    summary["documents"] = []

    # Try to retrieve all entries via the collection.get() API which is more
    # robust than assuming numeric ids. Different Chroma versions store ids
    # differently, so guard against missing keys.
    try:
        data = chroma_collection.get()
        metadatas = data.get('metadatas') if isinstance(data, dict) else None
        if metadatas:
            distinct_documents = set()
            for md in metadatas:
                if isinstance(md, dict):
                    distinct_documents.add(md.get('document', 'Unknown'))
            summary['documents'] = list(distinct_documents)
            # Update document_count if it was 0 but we found entries
            if summary['document_count'] == 0:
                summary['document_count'] = len(metadatas)
    except Exception:
        # Fall back to best-effort: leave documents empty
        pass

    # Best-effort fallback: if collection reports zero but collection was loaded
    # from a persistent sqlite, attempt to read the sqlite directly to surface
    # stored segments/metadata (useful when Chroma's SDK presents a different
    # logical API for persisted stores).
    if summary['document_count'] == 0:
        try:
            persist = getattr(chroma_collection, '_persist_path', None)
            if persist:
                import sqlite3
                dbfile = os.path.join(persist, 'chroma.sqlite3')
                if os.path.exists(dbfile):
                    conn = sqlite3.connect(dbfile)
                    cur = conn.cursor()
                    # count segments and try to read segment_metadata.document
                    try:
                        cur.execute('SELECT count(*) FROM segments')
                        seg_count = cur.fetchone()[0]
                        summary['document_count'] = seg_count
                    except Exception:
                        seg_count = 0
                    docs = set()
                    try:
                        cur.execute('SELECT * FROM segment_metadata')
                        for row in cur.fetchall():
                            # heuristic: look for a column that looks like a filename
                            for cell in row:
                                if isinstance(cell, str) and cell.endswith('.txt'):
                                    docs.add(cell)
                    except Exception:
                        pass
                    if docs:
                        summary['documents'] = list(docs)
                    conn.close()
        except Exception:
            pass

    print(json.dumps(summary, indent=2))
    return json.dumps(summary, indent=2)
