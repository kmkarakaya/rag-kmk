from rag_kmk import CONFIG
import json
import os
import logging
from enum import Enum
import typing

log = logging.getLogger(__name__)

# Minimal status enum for callers
class ChromaDBStatus(Enum):
	# Canonical statuses
	OK = "OK"
	NEW_PERSISTENT_CREATED = "NEW_PERSISTENT_CREATED"
	MISSING_PERSISTENT = "MISSING_PERSISTENT"
	MISSING_COLLECTION = "MISSING_COLLECTION"
	ALREADY_EXISTS = "ALREADY_EXISTS"   # returned when create_new=True but collection already exists
	ERROR = "ERROR"

	# Backwards-compatible aliases (older tests / callers expect these names)
	# EXISTING_* map to OK
	EXISTING_PERSISTENT = "OK"
	EXISTING_PERMANENT = "OK"
	# NEW_PERMANENT maps to new persistent creation
	NEW_PERMANENT = "NEW_PERSISTENT_CREATED"
	# Historic name for NEW_PERSISTENT_CREATED
	NEW_PERSISTENT = "NEW_PERSISTENT_CREATED"

# registry to map collection name -> client for helper lookup
_COLLECTION_CLIENTS = {}


def create_chroma_client(collection_name: str = 'default', chromaDB_path: str = None, create_new: bool = True, config: dict = None):
	"""
	Factory for chroma clients.

	- If chromaDB_path is provided and create_new=True: ensure folder exists and create/open the collection persistently.
	- If chromaDB_path is provided and create_new=False: open an existing persistent collection.
	- If chromaDB_path is None: the function returns a MISSING_PERSISTENT status (persistent path is required).
	Returns (client, collection, status).
	"""
	# Require a valid persistent chromaDB_path. If None is passed, return
	# a MISSING_PERSISTENT status to indicate the caller must provide a path.
	if chromaDB_path is None:
		log.error("create_chroma_client requires a persistent chromaDB_path; None was provided")
		return None, None, ChromaDBStatus.MISSING_PERSISTENT

	# Validate path
	if not isinstance(chromaDB_path, str) or not chromaDB_path.strip():
		log.error("Persistent chromaDB_path is required; invalid value provided.")
		return None, None, ChromaDBStatus.ERROR

	abs_path = os.path.abspath(chromaDB_path)

	# Ensure directory exists when creating new
	if create_new:
		try:
			os.makedirs(abs_path, exist_ok=True)
		except Exception as e:
			log.exception("Failed to create chromaDB directory %r: %s", abs_path, e)
			return None, None, ChromaDBStatus.ERROR
	else:
		# Loading existing persistent DB: require directory exist and be non-empty
		if not os.path.isdir(abs_path):
			log.error("Persistent chromaDB path does not exist: %r", abs_path)
			return None, None, ChromaDBStatus.MISSING_PERSISTENT
		try:
			entries = os.listdir(abs_path)
			if not entries:
				log.error("Persistent chromaDB path appears empty: %r", abs_path)
				return None, None, ChromaDBStatus.MISSING_PERSISTENT
		except Exception:
			log.exception("Failed to inspect chromaDB directory: %r", abs_path)
			return None, None, ChromaDBStatus.ERROR

	# Deferred import of chromadb and optional Settings (kept)
	try:
		import chromadb
		try:
			from chromadb.config import Settings
		except Exception:
			Settings = None
	except Exception as e:
		log.exception("chromadb library is required but not installed: %s", e)
		return None, None, ChromaDBStatus.ERROR

	# Instantiate client using modern API when available (preferred)
	client = None
	try:
		if hasattr(chromadb, "PersistentClient"):
			try:
				client = chromadb.PersistentClient(path=abs_path)
			except Exception as e:
				log.exception("chromadb.PersistentClient() raised: %s", e)
				return None, None, ChromaDBStatus.ERROR
		else:
			# fallback to older Client(Settings(...)) if PersistentClient not present
			if Settings is None:
				log.error("chromadb.PersistentClient not available and Settings unavailable.")
				return None, None, ChromaDBStatus.ERROR
			settings = Settings(chroma_db_impl="duckdb+parquet", persist_directory=abs_path)
			client = chromadb.Client(settings=settings)
	except Exception as e:
		log.exception("Failed to construct chromadb client at %r: %s", abs_path, e)
		return None, None, ChromaDBStatus.ERROR

	# Create or open the collection depending on create_new flag
	try:
		if create_new:
			# If caller requested creation, first check whether collection already exists.
			try:
				if hasattr(client, "list_collections"):
					names = client.list_collections()
					# list_collections may return names or collection objects; normalize
					existing_names = []
					if isinstance(names, list):
						for n in names:
							if isinstance(n, str):
								existing_names.append(n)
							else:
								# collection object: prefer .name or .id attribute
								existing_names.append(getattr(n, "name", None) or getattr(n, "id", None))
					# If the collection exists, do not recreate — return ALREADY_EXISTS
					if collection_name in existing_names:
						log.info("Requested create_new=True but collection %r already exists in %r", collection_name, abs_path)
						return None, None, ChromaDBStatus.ALREADY_EXISTS
			except Exception:
				# If list_collections fails, fall back to attempting to get_collection to detect existence
				try:
					if hasattr(client, "get_collection"):
						_ = client.get_collection(collection_name)
						# if get_collection succeeded then collection exists
						log.info("Requested create_new=True but collection %r already exists (detected via get_collection).", collection_name)
						return None, None, ChromaDBStatus.ALREADY_EXISTS
				except Exception:
					# get_collection failed so collection probably does not exist; proceed to create
					pass

			# collection does not exist; create or get it now
			if hasattr(client, "get_or_create_collection"):
				collection = client.get_or_create_collection(name=collection_name)
			else:
				try:
					collection = client.create_collection(name=collection_name)
				except Exception:
					collection = client.get_collection(collection_name)
			_COLLECTION_CLIENTS[collection_name] = client
			status = ChromaDBStatus.NEW_PERSISTENT_CREATED
			return client, collection, status
		else:
			# open-only: do NOT create the collection; require it to exist
			try:
				if hasattr(client, "get_collection"):
					collection = client.get_collection(collection_name)
				else:
					if hasattr(client, "list_collections"):
						names = client.list_collections()
						if isinstance(names, list) and collection_name in names:
							collection = client.get_collection(collection_name)
						else:
							return None, None, ChromaDBStatus.MISSING_COLLECTION
					else:
						collection = client.get_collection(collection_name)
				_COLLECTION_CLIENTS[collection_name] = client
				return client, collection, ChromaDBStatus.OK
			except Exception as e:
				log.debug("Failed to open existing collection %r: %s", collection_name, e)
				return None, None, ChromaDBStatus.MISSING_COLLECTION
	except Exception as e:
		log.exception("Failed while creating/opening collection %r in %r: %s", collection_name, abs_path, e)
		return None, None, ChromaDBStatus.ERROR


def get_client_for_collection(collection):
	"""Return client for a given collection object or None."""
	# Try to find by common attributes first
	try:
		# chromadb collection may have .client or ._client
		if hasattr(collection, "client"):
			return getattr(collection, "client")
		if hasattr(collection, "_client"):
			return getattr(collection, "_client")
		# fallback to registry by name
		name = getattr(collection, "name", None) or getattr(collection, "id", None)
		if name and name in _COLLECTION_CLIENTS:
			return _COLLECTION_CLIENTS[name]
	except Exception:
		pass
	return None

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

def _normalize_list_collections_result(raw) -> typing.List[str]:
	"""Normalize various shapes returned by client.list_collections() into a list of collection names."""
	names = []
	try:
		if raw is None:
			return names
		if isinstance(raw, list):
			for item in raw:
				if isinstance(item, str):
					names.append(item)
				elif hasattr(item, "name"):
					names.append(getattr(item, "name"))
				elif hasattr(item, "id"):
					names.append(getattr(item, "id"))
		elif isinstance(raw, dict):
			# some older APIs might return a mapping
			for k in raw.keys():
				names.append(str(k))
		else:
			# single object with .name / .id
			if hasattr(raw, "name"):
				names.append(getattr(raw, "name"))
			elif hasattr(raw, "id"):
				names.append(getattr(raw, "id"))
	except Exception:
		# best-effort: return whatever we've collected
		pass
	return names

def list_collection_names(client) -> typing.List[str]:
	"""Return a list of collection names for the provided chromadb client (best-effort)."""
	try:
		if hasattr(client, "list_collections"):
			raw = client.list_collections()
			return _normalize_list_collections_result(raw)
		# Some clients may expose collections via attribute
		if hasattr(client, "collections"):
			raw = getattr(client, "collections")
			return _normalize_list_collections_result(raw)
	except Exception:
		pass
	return []
