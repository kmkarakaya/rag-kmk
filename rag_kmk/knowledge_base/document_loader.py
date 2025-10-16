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
) -> Tuple[Optional[object], Optional[object]]:
    """
    Build or load a ChromaDB-backed knowledge base.

    Note:
    - If the caller omits chromaDB_path (the default sentinel), the function will prefer the config value.
    - If the caller explicitly passes chromaDB_path=None, that is treated as an explicit request for an in-memory collection
      when create_new=True.
    """
    # Resolve config: prefer explicit config arg, then package-level CONFIG, then load_config()
    cfg = config or getattr(rag_kmk, "CONFIG", None) or load_config()
    vcfg = cfg.get("vector_db", {}) if isinstance(cfg, dict) else {}

    collection_name = vcfg.get("collection_name", "default_collection")

    # Distinguish omitted vs explicit None
    if chromaDB_path is vdb_database._CHROMA_PATH_OMITTED:
        resolved_chroma_path = vcfg.get("chromaDB_path")
        chroma_path_was_explicit = False
    else:
        resolved_chroma_path = chromaDB_path
        chroma_path_was_explicit = True

    # Normalize legacy folder name 'chroma_db' -> 'chromaDB'
    if isinstance(resolved_chroma_path, str):
        rp_low = resolved_chroma_path.lower()
        if "chroma_db" in rp_low:
            normalized = resolved_chroma_path.replace("chroma_db", "chromaDB").replace("chroma_db".capitalize(), "chromaDB")
            if normalized != resolved_chroma_path:
                log.info(f"Normalizing chromaDB_path from {resolved_chroma_path!r} to {normalized!r}")
                print(f"[INFO] Normalizing chromaDB_path from {resolved_chroma_path!r} to {normalized!r}")
                resolved_chroma_path = normalized

    # Workflow debug prints
    print("---- build_knowledge_base workflow ----")
    print(f"collection_name: {collection_name}")
    print(f"chromaDB_path (resolved): {resolved_chroma_path!r}  (explicit arg provided: {chroma_path_was_explicit})")
    print(f"  (type: {type(resolved_chroma_path)})")
    print(f"create_new: {create_new}   add_documents: {add_documents}")
    print(f"vector_db config (vcfg): {vcfg}")

    # If no resolved path and create_new is False -> error
    if resolved_chroma_path is None and not create_new:
        raise ValueError(
            "chromaDB_path missing: caller did not provide a persistent path and create_new is False. "
            "Either provide a chromaDB_path, enable create_new to create a new collection, or pass an explicit "
            "chromaDB_path=None with create_new=True to create an in-memory collection."
        )

    # If caller explicitly requested in-memory (passed None explicitly) but didn't ask to create_new -> error
    if chroma_path_was_explicit and resolved_chroma_path is None and not create_new:
        raise ValueError("Explicit chromaDB_path=None was provided without create_new=True; cannot use in-memory without create_new.")

    chroma_collection, chroma_status = vdb_database.create_chroma_client(
        collection_name=collection_name,
        chromaDB_path=resolved_chroma_path,
        create_new=create_new,
        config=cfg,
    )

    # Print status returned from DB factory to make the workflow clear
    print("--------------------- CHROMADB STATUS ---------------------")
    try:
        print(chroma_status.value)
    except Exception:
        print(str(chroma_status))

    # Handle missing persistent collection specifically: return status instead of raising
    if chroma_status == vdb_database.ChromaDBStatus.MISSING_PERSISTENT:
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
        # Return status so caller can handle (run.py will print 'No documents loaded.')
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

