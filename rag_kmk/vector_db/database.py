from rag_kmk import CONFIG
_CHROMA_PATH_OMITTED = object()
import json
from enum import Enum
import os

# Define status enum
class ChromaDBStatus(Enum):
    EXISTING_PERMANENT = "Existing permanent collection found"
    NEW_PERMANENT = "New permanent collection created"
    NEW_MEMORY = "New in-memory collection created"
    FAILED_MEMORY = "New in-memory collection not created"
    
def create_chroma_client(chromaDB_path=_CHROMA_PATH_OMITTED, collection_name=None, sentence_transformer_model=None):
    """Create or open a Chroma client/collection.

    All CONFIG lookups are done lazily to avoid import-time side-effects.
    """
    # Lazy defaults from CONFIG
    db_cfg = CONFIG.get("vector_db", {}) if isinstance(CONFIG, dict) else {}
    # If caller did NOT provide chromaDB_path (left it omitted), fall back to config.
    # If caller passed chromaDB_path explicitly as None, treat that as a request
    # to create/use an in-memory collection.
    if chromaDB_path is _CHROMA_PATH_OMITTED:
        chromaDB_path = db_cfg.get("chromaDB_path")
    if collection_name is None:
        collection_name = db_cfg.get("collection_name")
    if sentence_transformer_model is None:
        sentence_transformer_model = db_cfg.get("embedding_model")

    status = None

    # Import heavy dependencies lazily
    try:
        from chromadb import Client, PersistentClient
        from chromadb.utils import embedding_functions
    except Exception:
        raise

    # Try to create the embedding function, but be tolerant in test or offline
    # environments where the sentence-transformers model may not be available.
    try:
        embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=sentence_transformer_model,
            device="cpu"  # Force CPU usage
        )
    except Exception as e:
        print("Warning: failed to initialize embedding function:", e)
        embedding_function = None
    
    if chromaDB_path is not None:
        # Normalize and validate: the package API expects a directory path
        chromaDB_path = os.path.abspath(chromaDB_path)
        # If a sqlite file was passed, instruct the user to pass the directory
        if os.path.isfile(chromaDB_path) and chromaDB_path.lower().endswith('.sqlite3'):
            raise ValueError(
                "chromaDB_path should be the Chroma persist directory, not the sqlite file path. "
                f"Pass the directory containing '{os.path.basename(chromaDB_path)}' instead."
            )

        print("Trying to access collection at ", chromaDB_path, " using Persistent Client")

        # Initialize the persistent client first; fail fast if client cannot be created
        try:
            chroma_client = PersistentClient(path=chromaDB_path)
        except Exception as e:
            print("Failed to initialize PersistentClient:", e)
            raise

        # Then try to get or create the collection using the client
        try:
            if embedding_function is not None:
                chroma_collection = chroma_client.get_collection(
                    collection_name,
                    embedding_function=embedding_function)
            else:
                chroma_collection = chroma_client.get_collection(collection_name)
            # Attach a diagnostic attribute to help summarize persistent DBs
            try:
                setattr(chroma_collection, '_persist_path', chromaDB_path)
                setattr(chroma_collection, '_chroma_client', chroma_client)
            except Exception:
                pass
            print(f"\tCollection {collection_name} found and uploaded!")
            status = ChromaDBStatus.EXISTING_PERMANENT
        except Exception:
            print(f"\tCollection {collection_name} does not exist")
            print("\tCreating a new collection")
            try:
                if embedding_function is not None:
                    chroma_collection = chroma_client.create_collection(
                        collection_name,
                        embedding_function=embedding_function)
                else:
                    chroma_collection = chroma_client.create_collection(collection_name)
                try:
                    setattr(chroma_collection, '_persist_path', chromaDB_path)
                    setattr(chroma_collection, '_chroma_client', chroma_client)
                except Exception:
                    pass
                print(f"\tCollection {collection_name} was created successfully")
                status = ChromaDBStatus.NEW_PERMANENT
            except Exception as e:
                print("Failed to create collection:", e)
                raise

    else:
        print("Using in-memory Client:")
        chroma_client = Client()
        try:
            # Use get_or_create_collection for robustness
            if embedding_function is not None:
                chroma_collection = chroma_client.get_or_create_collection(
                    name=collection_name,
                    embedding_function=embedding_function)
            else:
                chroma_collection = chroma_client.get_or_create_collection(name=collection_name)
            status = ChromaDBStatus.NEW_MEMORY
            print(f"\tCollection {collection_name} was created or retrieved successfully")
        except Exception as e:
            print(f"\tCollection {collection_name} was not created. Error: {e}")
            status = ChromaDBStatus.FAILED_MEMORY
            return None, None, status
    
    return chroma_client, chroma_collection, status


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
