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
						print(f"Total number of chunks (document split by max char = {len(text_chunksinChar)}): {len(text_chunksinChar)}")
						print(f"Total number of chunks (document split by {cfg.get('tokens_per_chunk', 'tokens_per_chunk')} tokens per chunk): {len(text_chunksinTokens)}")

						ids, metadatas = add_meta_data(text_chunksinTokens, filename, current_id)

						# Print before-insert collection size (use current_id as starting point)
						before_size = current_id
						print("Before inserting, the size of the collection: ", before_size)

						# Print a short preview of metadatas (avoid huge dumps)
						try:
							_preview = metadatas if (isinstance(metadatas, list) and len(metadatas) <= 50) else (metadatas[:50] if isinstance(metadatas, list) else "[unavailable]")
						except Exception:
							_preview = "[unavailable]"
						print("***** metadatas: *****")
						print(_preview)

						# perform insertion
						current_id += len(text_chunksinTokens)
						add_document_to_collection(ids, metadatas, text_chunksinTokens, chroma_collection)
						files_processed = True
						log.debug(f"Document {filename} added to the collection.")

						# If the DB module registered a client for this collection, call persist()
						try:
							client = vdb_database.get_client_for_collection(chroma_collection)
							persist_path = getattr(client, "_persist_path", None) if client is not None else None
							if client is not None:
								if hasattr(client, "persist"):
									print(f"Persisting chromadb client to disk at: {persist_path or '<unknown>'}")
									try:
										client.persist()
										print("chromadb client.persist() completed.")
									except Exception as e:
										log.warning("chromadb client.persist() raised: %s", e)
								elif hasattr(client, "persist_to_disk"):
									try:
										client.persist_to_disk()
									except Exception as e:
										log.warning("chromadb client.persist_to_disk() raised: %s", e)
								# verify persist folder contents if we know the path
								if persist_path:
									try:
										pfiles = os.listdir(os.path.abspath(persist_path))
										print("Persist directory now contains:", len(pfiles), "entries (example):", pfiles[:10])
									except Exception as e:
										log.warning("Failed to inspect persist directory %r: %s", persist_path, e)
						except Exception:
							# non-fatal
							pass

						# After insert, compute and print new size (robust)
						after_size = _resolve_collection_count(chroma_collection)
						print("After inserting, the size of the collection: ", after_size)
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
        document_directory_path: Optional[str] = vdb_database._CHROMA_PATH_OMITTED,
        chromaDB_path: Optional[str] = vdb_database._CHROMA_PATH_OMITTED,
        config: Optional[dict] = None,
        create_new: bool = False,
        add_documents: bool = True,
        force_persistence: Optional[bool] = None,  # New parameter: True => persistent, False => in-memory, None => unchanged behavior
) -> Tuple[Optional[object], Optional[object]]:
	"""
	Build or load a ChromaDB-backed knowledge base.

	Purpose
		Resolve the intended ChromaDB location, open an existing collection or create
		a new one (persistent or in-memory), and optionally ingest documents from a
		directory into that collection.

	Path resolution precedence (chromaDB_path)
		1. If the caller passes chromaDB_path as an explicit argument (including
		   explicit None), that value is used.
		2. Otherwise, if the provided config (or package CONFIG) contains
		   vector_db.chromaDB_path (for example the default './chromaDB' in config.yaml),
		   that config value is used and treated as a persistent path.
		3. If neither caller nor config provides a path, the resolved path is None.

	force_persistence semantics
		- None (default): preserve the resolved chromaDB_path behavior. If create_new is True
		  and chromaDB_path is None, an in-memory collection may be created.
		- True: require persistent storage. A non-empty resolved chromaDB_path is required
		  (either provided explicitly or present in config). Raises ValueError when no path.
		- False: force an in-memory collection by overriding any resolved path to None.
		  This behaves as if the caller explicitly passed chromaDB_path=None.

	Parameters
		document_directory_path (Optional[str]):
			Directory path with documents to ingest. If falsy, ingestion is skipped.
		chromaDB_path (Optional[str]):
			Caller-provided chromaDB path. Use the sentinel
			vdb_database._CHROMA_PATH_OMITTED to indicate "no explicit arg provided".
			Passing explicit None requests an in-memory collection.
		config (Optional[dict]):
			Optional configuration mapping. If not provided, package-level CONFIG or
			load_config() will be used. The vector_db section may contain chromaDB_path
			and collection_name.
		create_new (bool):
			If True, request creation of a new collection. If False, request loading an
			existing persistent collection (requires a persistent path).
		add_documents (bool):
			If True and a document_directory_path and collection are available, documents
			are ingested into the collection.
		force_persistence (Optional[bool]):
			If True: require persistent storage (chromaDB_path must be present).
			If False: force in-memory collection (overrides any path).
			If None: preserve default resolution behavior.

	Returns
		Tuple[chroma_collection, chroma_status]
			chroma_collection: handle/object for the opened/created ChromaDB collection,
						or None if operation failed or a persistent collection was
						requested but missing.
			chroma_status: an enum-like status from vdb_database (e.g. OK, NEW_MEMORY,
					MISSING_PERSISTENT, ERROR).

	Side effects
		- May write to disk when creating or persisting a persistent ChromaDB collection.
		- Calls vdb_database.create_chroma_client(); if documents are added, may call
			client.persist() / persist_to_disk if available.

	Exceptions
		- ValueError is raised for invalid caller combinations, for example:
			* force_persistence=True but no persistent path available (explicit or config).
			* explicit chromaDB_path=None without create_new=True (in-memory requested but not creation).
			* No persistent path resolved while create_new is False (attempt to load persistent without a path).
		- For database-factory conditions such as MISSING_PERSISTENT or ERROR the function
			prefers returning (None, chroma_status) rather than raising so callers can handle them.

	Examples (four common usage patterns)
		1) Load existing persistent collection and add documents:
			# 1.a - Explicit persistent location (custom folder)
			build_knowledge_base(document_directory_path='tests/sample_documents',
					chromaDB_path='./myVectorDB',
					create_new=False, add_documents=True)

			# 1.b - Use the configured default persistent location (omit chromaDB_path so
			#       the function falls back to vector_db.chromaDB_path in config.yaml, e.g. './chromaDB')
			build_knowledge_base(document_directory_path='tests/sample_documents',
					# chromaDB_path omitted -> use config default './chromaDB'
					create_new=False, add_documents=True)

		2) Load existing persistent collection without adding documents:
			# 2.a - Explicit persistent path, no ingestion
			build_knowledge_base(document_directory_path=None,
					chromaDB_path='./myVectorDB',
					create_new=False, add_documents=False)

			# 2.b - Use config default persistent path (omit chromaDB_path)
			build_knowledge_base(document_directory_path=None,
					# chromaDB_path omitted -> use config default './chromaDB'
					create_new=False, add_documents=False)

			# 2.c - (edge) Explicit None for chromaDB_path is invalid for load (create_new=False)
			#         so we show this as a commented example to indicate it's an error case:
			# build_knowledge_base(document_directory_path=None, chromaDB_path=None, create_new=False, add_documents=False)

		3) Create a new in-memory collection and add documents:
			# 3.a - Explicit in-memory (chromaDB_path=None)
			build_knowledge_base(document_directory_path='tests/sample_documents',
					chromaDB_path=None,
					create_new=True, add_documents=True)

			# 3.b - Force in-memory via force_persistence=False (overrides config)
			build_knowledge_base(document_directory_path='tests/sample_documents',
					# chromaDB_path omitted -> would normally use config; force in-memory below
					create_new=True, add_documents=True, force_persistence=False)

			# 3.c - Create an in-memory collection but still provide an explicit persistent path
			#       (the explicit path will be ignored if force_persistence=False)
			build_knowledge_base(document_directory_path='tests/sample_documents',
					chromaDB_path='./myVectorDB', create_new=True, add_documents=True, force_persistence=False)

		4) Create a new persistent collection and add documents (requires path or config):
			# 4.a - Explicit persistent path
			build_knowledge_base(document_directory_path='tests/sample_documents',
					chromaDB_path='./myVectorDB', create_new=True, add_documents=True, force_persistence=True)

			# 4.b - Use config default persistent path (omit chromaDB_path)
			build_knowledge_base(document_directory_path='tests/sample_documents',
					# chromaDB_path omitted -> use config default './chromaDB'
					create_new=True, add_documents=True, force_persistence=True)

			# 4.c - Passing chromaDB_path=None while requesting force_persistence=True is invalid
			#         (example shows what NOT to do):
			# build_knowledge_base(document_directory_path='tests/sample_documents', chromaDB_path=None, create_new=True, add_documents=True, force_persistence=True)

	Notes
		- The default chromaDB_path in config.yaml (for example './chromaDB') is treated as
			a persistent location unless the caller explicitly requests in-memory (chromaDB_path=None)
			or sets force_persistence=False.
		- Internal diagnostics record chroma_path_source (explicit | config | none) to make
			resolution behavior visible in logs/prints.
	"""
	# Resolve config: prefer explicit config arg; otherwise call load_config() and
	# treat its return value as authoritative for tests. Do NOT fall back to the
	# package-level CONFIG when load_config() is monkeypatched to return an empty
	# dict in tests — the tests expect load_config() to control resolution.
	if config is not None:
		cfg = config
	else:
		# load_config() may return {} when tests monkeypatch it; respect that.
		cfg = load_config()
	if not isinstance(cfg, dict):
		cfg = {}
	vcfg = cfg.get("vector_db", {}) if isinstance(cfg, dict) else {}

	collection_name = vcfg.get("collection_name", "default_collection")

	# Distinguish omitted vs explicit None and record source of resolution:
	# - 'explicit' : user passed chromaDB_path argument (could be None to request in-memory)
	# - 'config'   : resolved from config (this includes defaults like './chromaDB' in config.yaml)
	# - 'none'     : neither provided nor present in config
	if chromaDB_path is vdb_database._CHROMA_PATH_OMITTED:
		if "chromaDB_path" in vcfg:
			resolved_chroma_path = vcfg.get("chromaDB_path")
			chroma_path_was_explicit = False
			chroma_path_source = "config"
		else:
			resolved_chroma_path = None
			chroma_path_was_explicit = False
			chroma_path_source = "none"
	else:
		resolved_chroma_path = chromaDB_path
		chroma_path_was_explicit = True
		chroma_path_source = "explicit"

	# Normalize legacy folder name 'chroma_db' -> 'chromaDB' when a string path is present
	if isinstance(resolved_chroma_path, str):
		rp_low = resolved_chroma_path.lower()
		if "chroma_db" in rp_low:
			normalized = resolved_chroma_path.replace("chroma_db", "chromaDB").replace("chroma_db".capitalize(), "chromaDB")
			if normalized != resolved_chroma_path:
				log.info(f"Normalizing chromaDB_path from {resolved_chroma_path!r} to {normalized!r}")
				print(f"[INFO] Normalizing chromaDB_path from {resolved_chroma_path!r} to {normalized!r}")
				resolved_chroma_path = normalized

	# Apply force_persistence override if requested
	if force_persistence is True:
		# Caller requires persistent collection. Ensure we have a non-None path (could be from config/default).
		if not resolved_chroma_path:
			raise ValueError(
				"force_persistence=True requires a persistent chromaDB_path to be available. "
				"Provide chromaDB_path (explicitly or via config) when requesting a persistent creation."
			)
		log.info("force_persistence=True -> ensuring creation/opening of a persistent collection.")
	elif force_persistence is False:
		# Caller requires in-memory collection. Override any resolved path.
		resolved_chroma_path = None
		# mark as explicit (caller forced in-memory) to preserve later validation logic
		chroma_path_was_explicit = True
		chroma_path_source = "forced-in-memory"
		log.info("force_persistence=False -> forcing an in-memory collection (chromaDB_path=None).")

	# If the caller omitted chromaDB_path (it was taken from config) but intends to
	# add documents (ad-hoc ingestion), prefer creating an in-memory collection
	# unless the caller explicitly forced persistence.
	if not chroma_path_was_explicit and isinstance(resolved_chroma_path, str) and add_documents and force_persistence is not True:
		log.info("Omitted chromaDB_path from caller and add_documents=True -> prefer in-memory; ignoring config chromaDB_path=%r", resolved_chroma_path)
		resolved_chroma_path = None
		chroma_path_source = "implicit-inmemory-from-config"
		create_new = True

	# Workflow debug prints (include the source so defaults are visible)
	print("---- build_knowledge_base workflow ----")
	print(f"collection_name: {collection_name}")
	print(f"chromaDB_path (resolved): {resolved_chroma_path!r}  (source: {chroma_path_source}  explicit_arg: {chroma_path_was_explicit})")
	print(f"  (type: {type(resolved_chroma_path)})")
	print(f"create_new: {create_new}   add_documents: {add_documents}   force_persistence: {force_persistence!r}")
	print(f"vector_db config (vcfg): {vcfg}")

	# If resolved_chroma_path is None, decide creation intent:
	# - If caller explicitly passed chromaDB_path=None:
	#       * if create_new True or add_documents True -> treat as in-memory create
	#       * otherwise -> error (explicit None with no creation intent is invalid)
	# - If caller omitted chromaDB_path (config or none) and add_documents True and
	#   caller did not force persistence -> prefer in-memory creation (ignore config path)
	# - Otherwise (no path and not creating) raise ValueError because caller requested to load persistent.
	if resolved_chroma_path is None:
		if chroma_path_was_explicit:
			# explicit None
			if not create_new and not add_documents:
				raise ValueError("Explicit chromaDB_path=None was provided without create_new=True or add_documents=True; cannot proceed.")
			# allow in-memory creation when explicit None and either create_new or add_documents
			create_new = True
			chroma_path_source = "explicit-inmemory"
		else:
			# omitted path
			if add_documents and force_persistence is not True:
				# prefer in-memory creation for ad-hoc ingestion when user omitted chromaDB_path
				resolved_chroma_path = None
				create_new = True
				chroma_path_source = "implicit-inmemory"
			else:
				raise ValueError(
					"chromaDB_path missing: caller did not provide a persistent path and create_new is False. "
					"Either provide a chromaDB_path, enable create_new to create a new collection, or pass an explicit "
					"chromaDB_path=None with create_new=True to create an in-memory collection."
				)

	# Call the DB factory. Older versions returned (collection, status).
	# Newer versions return (client, collection, status). Accept both shapes.
	db_ret = vdb_database.create_chroma_client(
		collection_name=collection_name,
		chromaDB_path=resolved_chroma_path,
		create_new=create_new,
		config=cfg,
	)

	# Normalize returned tuple to (client, collection, status)
	client = None
	chroma_collection = None
	chroma_status = None
	try:
		if isinstance(db_ret, tuple) and len(db_ret) == 3:
			client, chroma_collection, chroma_status = db_ret
		elif isinstance(db_ret, tuple) and len(db_ret) == 2:
			chroma_collection, chroma_status = db_ret
			client = vdb_database.get_client_for_collection(chroma_collection)
		else:
			# Unexpected shape; try to unpack defensively
			chroma_collection, chroma_status = db_ret
	except Exception:
		# If unpacking fails, treat as error
		log.error("create_chroma_client returned unexpected value: %r", db_ret)
		return None, vdb_database.ChromaDBStatus.ERROR

	# Print status returned from DB factory to make the workflow clear
	print("--------------------- CHROMADB STATUS ---------------------")
	try:
		print(chroma_status.value)
	except Exception:
		print(str(chroma_status))

	# Handle missing persistent collection specifically.
	if chroma_status == vdb_database.ChromaDBStatus.MISSING_PERSISTENT:
		# If caller explicitly provided a persistent path and add_documents True,
		# they likely intended to create the collection here. Retry with create_new=True.
		if resolved_chroma_path and add_documents:
			log.info("Persistent collection missing; retrying with create_new=True to create at path %r", resolved_chroma_path)
			client2, chroma_collection2, chroma_status2 = vdb_database.create_chroma_client(
				collection_name=collection_name,
				chromaDB_path=resolved_chroma_path,
				create_new=True,
				config=cfg,
			)
			# normalize older return shape
			if isinstance(chroma_status2, vdb_database.ChromaDBStatus):
				chroma_collection = chroma_collection2
				chroma_status = chroma_status2
				client = client2
			else:
				# fallback: return original MISSING_PERSISTENT
				log.error("Retry to create persistent collection failed; original missing persistent returned.")
				return None, chroma_status
		else:
			err = (
				f"Requested persistent collection '{collection_name}' was not found in '{resolved_chroma_path}'.\n"
				"Requested intent: load existing persistent collection (create_new=False).\n"
				"Diagnostics:\n"
				f"  - resolved_chroma_path: {resolved_chroma_path!r}\n"
				f"  - collection_name: {collection_name}\n\n"
				"Recommended actions:\n"
				"  * Verify the path points to the correct ChromaDB persist directory.\n"
				"  * Confirm the collection name exists in that DB (use Chroma tooling or check directory contents).\n"
				"  * If you want to create a new persistent collection at this path, re-run with create_new=True.\n"
			)
			log.error(err)
			return None, chroma_status

	# If create_chroma_client failed, return status instead of raising
	if chroma_status == vdb_database.ChromaDBStatus.ERROR or chroma_collection is None:
		log.error(
			"Failed to create or load ChromaDB collection.\n"
			"Debug details:\n"
			f"  - collection_name: {collection_name}\n"
			f"  - resolved_chroma_path: {resolved_chroma_path!r} (explicit arg: {chroma_path_was_explicit})\n"
			f"  - create_new: {create_new}\n"
			f"  - add_documents: {add_documents}\n"
			f"  - CONFIG['vector_db']: {vcfg}\n"
		)
		return None, chroma_status

	# Catch mismatch: persistent requested but got NEW_MEMORY -> log and return status (avoid raising)
	if resolved_chroma_path is not None and create_new and chroma_status == vdb_database.ChromaDBStatus.NEW_MEMORY:
		msg = (
			"Requested to create new persistent collection at path but database factory returned NEW_MEMORY. "
			f"resolved_chroma_path={resolved_chroma_path!r} create_new={create_new}"
		)
		log.error(msg)
		return None, chroma_status

	# Only ingest documents when explicitly allowed and a directory path is provided
	if add_documents and document_directory_path and chroma_collection is not None:
		print("--------------------- INGEST DOCUMENTS ---------------------")
		print(f"Document directory: {document_directory_path}")
		print("Starting load_and_add_documents() ...")
		load_and_add_documents(chroma_collection, document_directory_path, cfg)
		print("Finished load_and_add_documents().")
	else:
		# explicit skip of ingestion or no collection available
		if not add_documents:
			print("add_documents=False -> skipping ingestion.")
		elif not document_directory_path:
			print("No document_directory_path provided -> skipping ingestion.")
		else:
			print("No chroma collection available -> skipping ingestion.")

	# Provide a concise summary if collection exists
	if chroma_collection is not None:
		print("--------------------- CHROMADB SUMMARY ---------------------\n")
		try:
			summarize = vdb_database.summarize_collection(chroma_collection)
		except Exception as e:
			print("Failed to summarize collection:", e)

	return chroma_collection, chroma_status

