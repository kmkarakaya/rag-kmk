from rag_kmk import CONFIG
import json
import os
import logging
from enum import Enum
import typing

log = logging.getLogger(__name__)

# Minimal status enum for callers
class ChromaDBStatus(Enum):
	CLIENT_READY = "CLIENT_READY"
	COLLECTION_CREATED = "COLLECTION_CREATED"
	COLLECTION_LOADED = "COLLECTION_LOADED"
	COLLECTION_LISTED = "COLLECTION_LISTED"
	SUMMARY_READY = "SUMMARY_READY"
	NEW_PERSISTENT_CREATED = "NEW_PERSISTENT_CREATED"
	# Backwards-compatible aliases
	EXISTING_PERSISTENT = "EXISTING_PERSISTENT"
	OK = "OK"
	MISSING_PERSISTENT = "MISSING_PERSISTENT"
	MISSING_COLLECTION = "MISSING_COLLECTION"
	ALREADY_EXISTS = "ALREADY_EXISTS"
	COLLECTION_DELETED = "COLLECTION_DELETED"
	COLLECTION_DELETE_MISSING = "COLLECTION_DELETE_MISSING"
	COLLECTION_DELETE_ERROR = "COLLECTION_DELETE_ERROR"
	ERROR = "ERROR"

# registry to map collection name -> client for helper lookup
_COLLECTION_CLIENTS = {}


def create_chromadb_client(chromaDB_path: str = None):
	"""
	Create or load a persistent ChromaDB client for the given path.
	If chromaDB_path is not provided, uses CONFIG['vector_db']['chromaDB_path'] or CONFIG['llm']['chromaDB_path'].
	Returns a dict: {'status': str, 'client': client or None, 'error': str or None}
	"""
	if chromaDB_path is None:
		# CONFIG may be None during tests or early import; guard accordingly
		cfg = CONFIG or {}
		chromaDB_path = (
			cfg.get('vector_db', {}).get('chromaDB_path')
			or cfg.get('llm', {}).get('chromaDB_path')
		)
	if chromaDB_path is None or not isinstance(chromaDB_path, str) or not chromaDB_path.strip():
		log.error("Persistent chromaDB_path is required; invalid value provided.")
		return {
			'status': ChromaDBStatus.MISSING_PERSISTENT.value,
			'client': None,
			'error': (
				"ChromaDB path is missing or invalid. "
				"Please set 'chromaDB_path' in your config under 'vector_db' or 'llm', "
				"or provide it explicitly when calling this function."
			)
		}

	abs_path = os.path.abspath(chromaDB_path)
	# Debug print suppressed; use logging instead when needed
	# print(f"[rag-kmk] create_chromadb_client: attempting to create/load client at: {abs_path}")
	log.info("create_chromadb_client: attempting to create/load client at %s", abs_path)
	try:
		import chromadb
		try:
			from chromadb.config import Settings
		except Exception:
			Settings = None
	except Exception as e:
		log.error("chromadb library is required but not installed: %s", e)
		# print(f"[rag-kmk] create_chromadb_client: chromadb import failed: {e}")
		return {
			'status': ChromaDBStatus.ERROR.value,
			'client': None,
			'error': (
				"ChromaDB library is not installed or failed to import. "
				"Please ensure 'chromadb' is installed in your environment. "
				f"Original error: {str(e)}"
			)
		}

	try:
		if hasattr(chromadb, "PersistentClient"):
			client = chromadb.PersistentClient(path=abs_path)
		else:
			if Settings is None:
				log.error("chromadb.PersistentClient not available and Settings unavailable.")
				return {
					'status': ChromaDBStatus.ERROR.value,
					'client': None,
					'error': (
						"Neither PersistentClient nor Settings are available in chromadb. "
						"Please check your chromadb installation/version."
					)
				}
			settings = Settings(chroma_db_impl="duckdb+parquet", persist_directory=abs_path)
			client = chromadb.Client(settings=settings)
	except Exception as e:
		log.error("Failed to construct chromadb client at %r: %s", abs_path, e)
		# print(f"[rag-kmk] create_chromadb_client: failed to construct client at {abs_path}: {e}")
		return {
			'status': ChromaDBStatus.ERROR.value,
			'client': None,
			'error': (
				f"Failed to construct ChromaDB client at '{abs_path}'. "
				"Check that the path is writable and chromadb is properly installed. "
				f"Original error: {str(e)}"
			)
		}

	# print(f"[rag-kmk] create_chromadb_client: client created/loaded successfully")
	log.info("create_chromadb_client: client created/loaded successfully at %s", abs_path)
	return {'status': ChromaDBStatus.CLIENT_READY.value, 'client': client, 'error': None}


# Backwards-compatible factory used by older tests/clients
def create_chroma_client(chromaDB_path: str = None, collection_name: str = None, create_new: bool = False, config: dict = None):
	"""Compatibility wrapper that mimics the older return signature: (client, collection, status)
	It maps to the new `create_chromadb_client` and attempts to open/create the requested collection.
	"""
	res = create_chromadb_client(chromaDB_path)
	client = res.get('client')
	if client is None:
		# Map error to status
		status = ChromaDBStatus.ERROR
		return None, None, status

	# If collection_name provided, attempt to load or create
	try:
		if collection_name:
			names = list_collection_names(client).get('collections', [])
			if collection_name in names:
				_, collection = load_collection(client, collection_name)
				return client, collection, ChromaDBStatus.OK
			else:
				result, collection = create_collection(client, collection_name)
				if result.get('status') == ChromaDBStatus.COLLECTION_CREATED.value:
					return client, collection, ChromaDBStatus.NEW_PERSISTENT_CREATED
				else:
					return client, collection, ChromaDBStatus.ERROR
		# no collection requested: return client and OK
		return client, None, ChromaDBStatus.OK
	except Exception:
		return None, None, ChromaDBStatus.ERROR

def create_collection(client, collection_name: str):
	"""
	Create a new collection in the given client.
	Returns (result_dict, collection or None)
	"""
	try:
		names = list_collection_names(client)['collections']
		# print(f"[rag-kmk] create_collection: existing collections: {names}")
		log.info("create_collection: existing collections: %s", names)
		if collection_name in names:
			# print(f"[rag-kmk] create_collection: collection already exists: {collection_name}")
			result = {
				'status': ChromaDBStatus.ALREADY_EXISTS.value,
				'error': (
					f"Collection '{collection_name}' already exists. "
					"Collection names must be unique. "
					"Please try a different name that does not conflict with existing collections."
				)
			}
			return result, None
		if hasattr(client, "get_or_create_collection"):
			collection = client.get_or_create_collection(name=collection_name)
		else:
			collection = client.create_collection(name=collection_name)
		_COLLECTION_CLIENTS[collection_name] = client
		# print(f"[rag-kmk] create_collection: created collection: {collection_name}")
		log.info("create_collection: created collection: %s", collection_name)
		result = {'status': ChromaDBStatus.COLLECTION_CREATED.value, 'error': None}
		return result, collection
	except Exception as e:
		log.exception("Failed to create collection %r: %s", collection_name, e)
		# print(f"[rag-kmk] create_collection: error creating collection {collection_name}: {e}")
		result = {
			'status': ChromaDBStatus.ERROR.value,
			'error': (
				f"Failed to create collection '{collection_name}'. "
				"Check that the client is valid and the name is allowed. "
				f"Original error: {str(e)}"
			)
		}
		return result, None

def load_collection(client, collection_name: str):
	"""
	Load an existing collection from the given client.
	Returns (result_dict, collection or None)
	"""
	try:
		names = list_collection_names(client)['collections']
		# print(f"[rag-kmk] load_collection: available collections: {names}")
		log.info("load_collection: available collections: %s", names)
		if collection_name not in names:
			# print(f"[rag-kmk] load_collection: missing collection: {collection_name}")
			result = {
				'status': ChromaDBStatus.MISSING_COLLECTION.value,
				'error': (
					f"Collection '{collection_name}' does not exist in the database. "
					"Please check the name or create the collection first."
				)
			}
			return result, None
		collection = client.get_collection(collection_name)
		_COLLECTION_CLIENTS[collection_name] = client
		# print(f"[rag-kmk] load_collection: loaded collection: {collection_name}")
		result = {'status': ChromaDBStatus.COLLECTION_LOADED.value, 'error': None}
		return result, collection
	except Exception as e:
		log.debug("Failed to load collection %r: %s", collection_name, e)
		# print(f"[rag-kmk] load_collection: error loading collection {collection_name}: {e}")
		result = {
			'status': ChromaDBStatus.ERROR.value,
			'error': (
				f"Failed to load collection '{collection_name}'. "
				"Check that the client is valid and the collection exists. "
				f"Original error: {str(e)}"
			)
		}
		return result, None

def summarize_collection(chroma_collection):
	"""
	Return a summary dict for the collection: {'status': str, 'summary': dict, 'error': str or None}
	"""
	if chroma_collection is None:
		return {'status': 'NO_COLLECTION', 'summary': {}, 'error': "No chroma collection available to summarize."}
	summary = {}
	try:
		summary["collection_name"] = getattr(chroma_collection, 'name', 'unknown')
	except Exception:
		summary["collection_name"] = 'unknown'

	try:
		total = chroma_collection.count()
	except Exception:
		total = 0
	summary["document_count"] = total
	summary["documents"] = []

	try:
		data = chroma_collection.get()
		metadatas = data.get('metadatas') if isinstance(data, dict) else None
		if metadatas:
			distinct_documents = set()
			for md in metadatas:
				if isinstance(md, dict):
					distinct_documents.add(md.get('document', 'Unknown'))
			summary['documents'] = list(distinct_documents)
			if summary['document_count'] == 0:
				summary['document_count'] = len(metadatas)
	except Exception:
		pass

	if summary['document_count'] == 0:
		try:
			persist = getattr(chroma_collection, '_persist_path', None)
			if persist:
				import sqlite3
				dbfile = os.path.join(persist, 'chroma.sqlite3')
				if os.path.exists(dbfile):
					conn = sqlite3.connect(dbfile)
					cur = conn.cursor()
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

	return {'status': ChromaDBStatus.SUMMARY_READY.value, 'summary': summary, 'error': None}

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

def list_collection_names(client) -> dict:
	"""
	Return a dict: {'status': str, 'collections': list, 'error': str or None}
	"""
	try:
		if hasattr(client, "list_collections"):
			raw = client.list_collections()
			names = _normalize_list_collections_result(raw)
			# print(f"[rag-kmk] list_collection_names: found collections: {names}")
			log.info("list_collection_names: found collections: %s", names)
			return {'status': ChromaDBStatus.COLLECTION_LISTED.value, 'collections': names, 'error': None}
		if hasattr(client, "collections"):
			raw = getattr(client, "collections")
			names = _normalize_list_collections_result(raw)
			return {'status': ChromaDBStatus.COLLECTION_LISTED.value, 'collections': names, 'error': None}
	except Exception as e:
		# print(f"[rag-kmk] list_collection_names: error: {e}")
		return {'status': ChromaDBStatus.ERROR.value, 'collections': [], 'error': str(e)}
	return {'status': ChromaDBStatus.COLLECTION_LISTED.value, 'collections': [], 'error': None}

def delete_collection(
	client,
	collection_name: str
) -> dict:
	"""
	Remove a persistent ChromaDB collection from the database.
	Also removes any in-memory handles.
	Returns a dict: {'status': str, 'success': bool, 'error': str or None}
	"""
	# Remove from ChromaDB
	try:
		if hasattr(client, "delete_collection"):
			# print(f"[rag-kmk] delete_collection: deleting collection {collection_name}")
			log.info("delete_collection: deleting collection %s", collection_name)
			client.delete_collection(name=collection_name)
		else:
			# print(f"[rag-kmk] delete_collection: client does not support delete_collection()")
			log.warning("delete_collection: Client does not support delete_collection().")
	except Exception as e:
		log.warning(f"delete_collection: Could not delete collection '{collection_name}' from client: {e}")
		# print(f"[rag-kmk] delete_collection: error while deleting {collection_name}: {e}")
		return {
			'status': ChromaDBStatus.COLLECTION_DELETE_ERROR.value,
			'success': False,
			'error': f"Failed to delete collection from database: {e}"
		}

	# Remove in-memory handle
	_COLLECTION_CLIENTS.pop(collection_name, None)

	# print(f"[rag-kmk] delete_collection: finished deletion attempt for {collection_name}")
	log.info("delete_collection: finished deletion attempt for %s", collection_name)
	return {
		'status': ChromaDBStatus.COLLECTION_DELETED.value,
		'success': True,
		'error': None
	}


