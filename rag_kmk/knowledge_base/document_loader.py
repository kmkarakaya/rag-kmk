import os
import fitz  # PyMuPDF==1.26.5
import logging
from docx.opc.exceptions import PackageNotFoundError
import rag_kmk
from rag_kmk.knowledge_base.text_splitter import (
	convert_Pages_ChunkinChar,
	convert_Chunk_Token,
	add_meta_data,
	add_document_to_collection,
)
from typing import Optional, Tuple
import rag_kmk
from rag_kmk.config.config import load_config
from rag_kmk.vector_db import database as vdb_database


log = logging.getLogger(__name__)

def _resolve_collection_count(collection) -> int:
    """
    Robustly determine number of items in a chroma collection across chromadb versions.
    """
    try:
        res = collection.count()
        if isinstance(res, int):
            return res
        if isinstance(res, dict):
            return int(res.get("count") or sum(res.values()))
    except TypeError:
        try:
            res = collection.count({})
            if isinstance(res, int):
                return res
            if isinstance(res, dict):
                return int(res.get("count") or sum(res.values()))
        except Exception:
            pass
    except Exception:
        pass

    try:
        data = collection.get(include=["ids"])
        if isinstance(data, dict) and "ids" in data:
            return len(data["ids"])
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list):
                    return len(v)
        if isinstance(data, list):
            return len(data)
    except Exception:
        pass

    return 0


def load_and_add_documents(chroma_collection, document_directory_path, cfg):
	"""Scans a directory for documents, processes them, and adds them to the collection."""
	current_id = _resolve_collection_count(chroma_collection)
	log.debug(f"Current number of document chunks in Vector DB: {current_id}")

	# Document directory: <object object ...> was causing TypeError in os.stat
	# Guard against non-path inputs (None or unexpected sentinel); skip ingestion.
	if not document_directory_path or not isinstance(document_directory_path, (str, bytes, os.PathLike)):
		print(f"Document directory: {document_directory_path!r} (invalid or None) - skipping document ingestion.")
		return

	# Now safe to check filesystem
	if not os.path.isdir(document_directory_path):
		print(f"Document directory not found: {document_directory_path!r} - skipping document ingestion.")
		return

	# Validate directory
	if not os.path.isdir(document_directory_path):
		log.error(f"Invalid directory path: '{document_directory_path}'. Please provide a valid directory.")
		raise ValueError(f"Invalid directory path: '{document_directory_path}'. Please provide a valid directory.")

	files_processed = False
	error_messages = []

	log.info(f"Scanning for documents in '{document_directory_path}'...")
	for filename in os.listdir(document_directory_path):
		file_path = os.path.join(document_directory_path, filename)
		file_extension = os.path.splitext(filename)[1]
		document = []

		supported_types = cfg.get('supported_file_types', ['.txt', '.pdf', '.docx'])
		if file_extension in supported_types:
			try:
				if file_extension == '.txt':
					try:
						with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
							text = ''
							chunk_size = 1024 * 1024
							while True:
								chunk = file.read(chunk_size)
								if not chunk:
									break
								text += chunk
							if text:
								document.append(text.strip())
								log.debug(f'Text document {filename} loaded successfully.')
							else:
								log.warning(f"Skipping empty or unreadable .txt file: {filename}")
					except FileNotFoundError:
						log.error(f"File not found: {file_path}")
						error_messages.append(f"File not found: {file_path}")
					except UnicodeDecodeError:
						log.error(f"Could not decode file {file_path} with UTF-8.")
						error_messages.append(f"Could not decode file {file_path} with UTF-8.")
					except Exception as e:
						log.exception(f"An unexpected error occurred while processing {file_path}")
						error_messages.append(f"An unexpected error occurred while processing {file_path}: {e}")

				elif file_extension == '.pdf':
					with fitz.open(file_path) as doc:
						text = ''
						for page in doc:
							text += page.get_text()
						document.append(text)
					log.debug(f'PDF document {filename} loaded successfully.')

				elif file_extension == '.docx':
					try:
						# Import docx2txt lazily so tests and other imports don't require it at module-import time
						try:
							import docx2txt
						except ImportError:
							log.error(f"docx2txt library not found. Please install it using 'pip install docx2txt'. Skipping '{filename}'.")
							continue
						text = docx2txt.process(file_path)
						document.append(text)
						if not text:
							raise ValueError(f"No text extracted from {filename}")
						log.debug(f"DOCX document '{filename}' loaded successfully. Text length: {len(text)} characters.")
					except Exception as e:
						error_messages.append(f"Failed to load document '{filename}': {e}")
						log.exception(f"Failed to load document from '{file_path}'")
						continue

				# Splitting and storing
				if document:
					try:
						# compute chunks
						text_chunksinChar = convert_Pages_ChunkinChar(document)
						text_chunksinTokens = convert_Chunk_Token(text_chunksinChar)

						# Informational debug output about splitting
						log.info("Document %s: split into %d char-based chunks and %d token-based chunks.",
						         filename, len(text_chunksinChar), len(text_chunksinTokens))

						ids, metadatas = add_meta_data(text_chunksinTokens, filename, current_id)

						# Print before-insert collection size (use current_id as starting point)
						before_size = current_id
						log.info("Before inserting, collection size (approx): %d", before_size)

						# Print a short preview of metadatas (avoid huge dumps)
						try:
							_preview = (metadatas if (isinstance(metadatas, list) and len(metadatas) <= 10)
							            else (metadatas[:10] if isinstance(metadatas, list) else "[unavailable]"))
						except Exception:
							_preview = "[unavailable]"
						# full metadata can be large — expose at debug level
						log.debug("Metadatas preview for %s: %s", filename, _preview)

						# perform insertion
						current_id += len(text_chunksinTokens)
						add_document_to_collection(ids, metadatas, text_chunksinTokens, chroma_collection)
						files_processed = True
						log.info("Inserted %d chunks from %s into collection.", len(text_chunksinTokens), filename)

						# If the DB module registered a client for this collection, call persist()
						try:
							client = vdb_database.get_client_for_collection(chroma_collection)
							# best-effort discovery of persist path for user feedback
							persist_path = None
							if client is not None:
								persist_path = getattr(client, "_persist_path", None) or getattr(client, "path", None) or getattr(client, "_path", None)
								if hasattr(client, "persist"):
									try:
										client.persist()
										log.info("Client.persist() completed. persist_path=%s", persist_path or "<unknown>")
									except Exception as e:
										log.warning("Client.persist() raised exception: %s", e)
								elif hasattr(client, "persist_to_disk"):
									try:
										client.persist_to_disk()
										log.info("Client.persist_to_disk() completed.")
									except Exception as e:
										log.warning("Client.persist_to_disk() raised exception: %s", e)
								else:
									# If using the JSON fallback client, persist() may be a no-op but path will be available
									log.debug("Client has no explicit persist() method; persist_path=%s", persist_path or "<unknown>")
								# verify persist folder contents if we know the path (debug only)
								if persist_path:
									try:
										pfiles = os.listdir(os.path.abspath(persist_path))
										log.debug("Persist directory %s contains %d entries (example): %s", persist_path, len(pfiles), pfiles[:10])
									except Exception as e:
										log.warning("Failed to inspect persist directory %r: %s", persist_path, e)
						except Exception:
							# non-fatal
							pass

						# After insert, compute and print new size (robust)
						after_size = _resolve_collection_count(chroma_collection)
						log.info("After inserting, the size of the collection: %d", after_size)
					except Exception as e:
						log.error(f"Failed to process and add document '{filename}' to the collection: {e}")
						error_messages.append(f"Failed to process and add document '{filename}': {e}")
			except (FileNotFoundError, fitz.EmptyFileError, PackageNotFoundError, UnicodeDecodeError) as e:
				error_messages.append(f"Failed to load document '{filename}': {e}. Try specifying encoding.")
				log.exception(f'Failed to load document from {file_path}')
				continue
			except Exception as e:
				error_messages.append(f"Failed to load document '{filename}': {e}")
				log.exception(f'Failed to load document from {file_path}')
				continue

		else:
			log.debug(f'Skipping unsupported file type: {file_path}')
	
	if not files_processed:
		log.error("No files were successfully processed. Errors encountered:")
		for error in error_messages:
			log.error(f"  - {error}")
	
	return files_processed, error_messages


def build_knowledge_base(
	collection_name: str,
	document_directory_path=None,
	create_new: bool = False,
	add_documents: bool = False,
	cfg=None):
	"""
	Simplified persistent-only behavior.

	- collection_name (str): required name of the collection to create or open.
	- chromaDB_path is always taken from config['vector_db']['chromaDB_path'].
	- create_new=True: create persistent DB directory if needed and create-or-get the collection.
	- create_new=False: require persistent DB and collection exist.
	Returns (chroma_collection, chroma_status).
	"""
	# Resolve configuration (cfg arg overrides load_config())
	if cfg is None:
		cfg = load_config() or {}
	if not isinstance(cfg, dict):
		cfg = {}
	vcfg = cfg.get("vector_db", {}) if isinstance(cfg, dict) else {}

	# Always read chromaDB path from config
	resolved_chroma_path = vcfg.get("chromaDB_path")
	if not isinstance(resolved_chroma_path, str) or not resolved_chroma_path.strip():
		raise ValueError("A persistent chromaDB_path must be set in the config (vector_db.chromaDB_path). In-memory is not supported.")

	# Ensure persistent folder for create_new; for load require it to exist
	abs_path = os.path.abspath(resolved_chroma_path)
	if create_new:
		try:
			os.makedirs(abs_path, exist_ok=True)
		except Exception as e:
			log.exception("Failed to create persistent chromaDB directory %r: %s", abs_path, e)
			return None, vdb_database.ChromaDBStatus.ERROR
	else:
		if not os.path.isdir(abs_path):
			# Caller attempted to open existing DB but path not found
			log.error("Requested to open persistent ChromaDB at %r but directory was not found.", abs_path)
			print(f"ERROR: Persistent ChromaDB path not found: {abs_path!r}")
			print("To create a new persistent DB at that location, run with create_new=True.")
			return None, vdb_database.ChromaDBStatus.MISSING_PERSISTENT

	# Call the DB factory (factory handles collection create/open)
	try:
		db_ret = vdb_database.create_chroma_client(
			collection_name=collection_name,
			chromaDB_path=abs_path,
			create_new=create_new,
			config=cfg,
		)
	except Exception as e:
		# Simple failure: give concise actionable message
		log.exception("create_chroma_client failed for path %r: %s", abs_path, e)
		print(f"\nERROR: Unable to create/open persistent ChromaDB at {abs_path!r}: {e}")
		print("Ensure the configured 'vector_db.chromaDB_path' is correct and writable, and")
		print("install a modern 'chromadb' package that provides PersistentClient(path=...) if you want to use the chromadb client.")
		return None, vdb_database.ChromaDBStatus.ERROR

	# Normalize returned tuple to (client, collection, status) or (collection, status)
	client = None
	chroma_collection = None
	chroma_status = None
	try:
		if isinstance(db_ret, tuple) and len(db_ret) == 3:
			client, chroma_collection, chroma_status = db_ret
		elif isinstance(db_ret, tuple) and len(db_ret) == 2:
			chroma_collection, chroma_status = db_ret
		else:
			# defensive fallback
			chroma_collection, chroma_status = db_ret
	except Exception:
		log.error("create_chroma_client returned unexpected value: %r", db_ret)
		return None, vdb_database.ChromaDBStatus.ERROR

	# Propagate DB factory statuses as simple returns (caller can inspect chroma_status)
	if chroma_status == vdb_database.ChromaDBStatus.MISSING_PERSISTENT:
		log.error("create_chroma_client reported MISSING_PERSISTENT for path %r", abs_path)
		print(f"ERROR: Persistent ChromaDB not found: {abs_path!r}. Set create_new=True to create a new DB.")
		# Provide a short actionable summary for callers
		summary_message = {
			"action": "open",
			"path": abs_path,
			"collection": collection_name,
			"result": "missing_persistent",
			"create_new": create_new,
			"add_documents": add_documents,
		}
		print("CHROMADB ACTION SUMMARY:", summary_message)
		return None, chroma_status
	if chroma_status == vdb_database.ChromaDBStatus.MISSING_COLLECTION:
		log.error("create_chroma_client reported MISSING_COLLECTION for collection %r in %r", collection_name, abs_path)
		print(f"ERROR: Collection {collection_name!r} not found in persistent ChromaDB at {abs_path!r}.")
		summary_message = {
			"action": "open",
			"path": abs_path,
			"collection": collection_name,
			"result": "missing_collection",
			"create_new": create_new,
			"add_documents": add_documents,
		}
		print("CHROMADB ACTION SUMMARY:", summary_message)
		return None, chroma_status
	# NEW: If caller asked to create_new but collection already exists, surface a clear error.
	if chroma_status == vdb_database.ChromaDBStatus.ALREADY_EXISTS:
		log.error("create_chroma_client reported ALREADY_EXISTS for collection %r in %r", collection_name, abs_path)
		print(f"ERROR: Cannot create collection {collection_name!r} because it already exists in persistent ChromaDB at {abs_path!r}.")
		print("If you intended to open the existing collection, call with create_new=False.")
		print("If you want to overwrite it (destructive), remove the existing collection first using the DB admin tools.")
		# Return error status so callers know creation did not proceed
		return None, chroma_status
	if chroma_status == vdb_database.ChromaDBStatus.ERROR or chroma_collection is None:
		log.error("create_chroma_client returned ERROR or no collection for %r at %r (status=%r)", collection_name, abs_path, chroma_status)
		print("ERROR: Failed to create or open the collection. See logs for details.")
		summary_message = {
			"action": "open_or_create",
			"path": abs_path,
			"collection": collection_name,
			"result": "error",
			"create_new": create_new,
			"add_documents": add_documents,
		}
		print("CHROMADB ACTION SUMMARY:", summary_message)
		return None, chroma_status

	# --- NEW: Clear, explicit messages about open/create and ingestion choice ---
	try:
		current_count = _resolve_collection_count(chroma_collection)
	except Exception:
		current_count = None

	action = "created" if create_new else "opened"
	print(f"{action.capitalize()} persistent ChromaDB collection '{collection_name}' at: {abs_path!r}")

	if current_count is not None:
		print(f"Collection '{collection_name}' current size (items/chunks): {current_count}")

	# Only ingest when explicitly requested by the caller
	if not add_documents:
		print("add_documents=False -> skipping ingestion of documents into the collection.")
		# produce the action summary reflecting the user's request and actual outcome
		summary_message = {
			"action": action,
			"path": abs_path,
			"collection": collection_name,
			"result": "opened" if not create_new else "created",
			"collection_size": current_count,
			"ingestion_requested": False,
			"ingestion_performed": False,
		}
		print("CHROMADB ACTION SUMMARY:", summary_message)
		# return the opened/created collection without performing ingestion
		return chroma_collection, chroma_status

	# If we reach here, add_documents is True and we will ingest (document_directory_path must be provided)
	if not document_directory_path:
		print("add_documents=True but no document_directory_path provided -> skipping ingestion.")
		summary_message = {
			"action": action,
			"path": abs_path,
			"collection": collection_name,
			"result": "opened" if not create_new else "created",
			"collection_size": current_count,
			"ingestion_requested": True,
			"ingestion_performed": False,
			"note": "no document_directory_path provided"
		}
		print("CHROMADB ACTION SUMMARY:", summary_message)
		return chroma_collection, chroma_status

	print("INGEST: starting document ingestion into collection:", collection_name)
	processed, errors = load_and_add_documents(chroma_collection, document_directory_path, cfg)
	ingested_any = bool(processed)
	# build and print final summary including ingestion outcome
	summary_message = {
		"action": action,
		"path": abs_path,
		"collection": collection_name,
		"result": "opened" if not create_new else "created",
		"collection_size_before": current_count,
		"ingestion_requested": True,
		"ingestion_performed": ingested_any,
		"ingestion_errors": errors if errors else None,
	}
	print("CHROMADB ACTION SUMMARY:", summary_message)

	if not processed:
		print("No files processed during ingestion. Errors:", errors)

	# Return the collection and status to keep compatibility with callers expecting (kb, chromaDB_status)
	return chroma_collection, chroma_status

