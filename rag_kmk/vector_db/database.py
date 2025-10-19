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
		chromaDB_path = (
			CONFIG.get('vector_db', {}).get('chromaDB_path')
			or CONFIG.get('llm', {}).get('chromaDB_path')
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
	try:
		import chromadb
		try:
			from chromadb.config import Settings
		except Exception:
			Settings = None
	except Exception as e:
		log.error("chromadb library is required but not installed: %s", e)
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
		return {
			'status': ChromaDBStatus.ERROR.value,
			'client': None,
			'error': (
				f"Failed to construct ChromaDB client at '{abs_path}'. "
				"Check that the path is writable and chromadb is properly installed. "
				f"Original error: {str(e)}"
			)
		}

	return {'status': ChromaDBStatus.CLIENT_READY.value, 'client': client, 'error': None}

def create_collection(client, collection_name: str):
	"""
	Create a new collection in the given client.
	Returns (result_dict, collection or None)
	"""
	try:
		names = list_collection_names(client)['collections']
		if collection_name in names:
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
		result = {'status': ChromaDBStatus.COLLECTION_CREATED.value, 'error': None}
		return result, collection
	except Exception as e:
		log.exception("Failed to create collection %r: %s", collection_name, e)
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
		if collection_name not in names:
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
		result = {'status': ChromaDBStatus.COLLECTION_LOADED.value, 'error': None}
		return result, collection
	except Exception as e:
		log.debug("Failed to load collection %r: %s", collection_name, e)
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
			return {'status': ChromaDBStatus.COLLECTION_LISTED.value, 'collections': names, 'error': None}
		if hasattr(client, "collections"):
			raw = getattr(client, "collections")
			names = _normalize_list_collections_result(raw)
			return {'status': ChromaDBStatus.COLLECTION_LISTED.value, 'collections': names, 'error': None}
	except Exception as e:
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
			client.delete_collection(name=collection_name)
		else:
			log.warning("delete_collection: Client does not support delete_collection().")
	except Exception as e:
		log.warning(f"delete_collection: Could not delete collection '{collection_name}' from client: {e}")
		return {
			'status': ChromaDBStatus.COLLECTION_DELETE_ERROR.value,
			'success': False,
			'error': f"Failed to delete collection from database: {e}"
		}

	# Remove in-memory handle
	_COLLECTION_CLIENTS.pop(collection_name, None)

	return {
		'status': ChromaDBStatus.COLLECTION_DELETED.value,
		'success': True,
		'error': None
	}


