import os
import logging
from typing import Optional, Tuple

import fitz  # PyMuPDF==1.26.5
from docx.opc.exceptions import PackageNotFoundError

from rag_kmk.knowledge_base.text_splitter import (
	convert_Pages_ChunkinChar,
	convert_Chunk_Token,
	add_meta_data,
	add_document_to_collection,
)
from rag_kmk.config.config import load_config
from rag_kmk.vector_db import database as vdb_database


log = logging.getLogger(__name__)


def _validate_document_directory(document_directory_path) -> bool:
	"""Return True if the provided path looks like a valid existing directory."""
	if not document_directory_path or not isinstance(document_directory_path, (str, bytes, os.PathLike)):
		return False
	try:
		return os.path.isdir(document_directory_path)
	except Exception:
		return False


def _resolve_collection_count(collection) -> int:
	"""Robustly determine number of items in a chroma collection across chromadb versions.

	This helper is forgiving and used by ingestion/reporting code and tests.
	"""
	if collection is None:
		return 0
	# Try count() variants
	try:
		res = collection.count()
		if isinstance(res, int):
			return res
		if isinstance(res, dict):
			return int(res.get("count") or sum(v for v in res.values() if isinstance(v, int)))
	except TypeError:
		try:
			res = collection.count({})
			if isinstance(res, int):
				return res
			if isinstance(res, dict):
				return int(res.get("count") or sum(v for v in res.values() if isinstance(v, int)))
		except Exception:
			pass
	except Exception:
		pass

	# Fallback to get()/ids
	try:
		data = collection.get(include=["ids"]) if hasattr(collection, "get") else None
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
	"""Scan a directory, split found documents and add them to `chroma_collection`.

	Returns (files_processed: bool, errors: list[str]).
	"""
	if cfg is None:
		cfg = {}

	if not _validate_document_directory(document_directory_path):
		return False, [f"Document directory not found or invalid: {document_directory_path!r}"]

	current_id = _resolve_collection_count(chroma_collection)
	files_processed = False
	error_messages = []

	supported_types = cfg.get("supported_file_types", [".txt", ".pdf", ".docx"]) if isinstance(cfg, dict) else [".txt", ".pdf", ".docx"]

	for filename in sorted(os.listdir(document_directory_path)):
		file_path = os.path.join(document_directory_path, filename)
		if not os.path.isfile(file_path):
			continue
		_, file_extension = os.path.splitext(filename)
		if file_extension not in supported_types:
			log.debug("Skipping unsupported file type: %s", file_path)
			continue

		try:
			# Load content
			content_parts = []
			if file_extension == ".txt":
				try:
					with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
						content_parts.append(fh.read())
				except Exception as e:
					log.exception("Failed to read text file %s", file_path)
					error_messages.append(str(e))
					continue

			elif file_extension == ".pdf":
				try:
					with fitz.open(file_path) as doc:
						text = "".join(p.get_text() for p in doc)
						content_parts.append(text)
				except Exception as e:
					log.exception("Failed to read PDF %s", file_path)
					error_messages.append(str(e))
					continue

			elif file_extension == ".docx":
				try:
					try:
						import docx2txt  # lazy
					except ImportError:
						log.error("docx2txt not installed; skipping %s", file_path)
						error_messages.append("docx2txt not installed")
						continue
					text = docx2txt.process(file_path)
					content_parts.append(text)
				except Exception as e:
					log.exception("Failed to load DOCX %s", file_path)
					error_messages.append(str(e))
					continue

			# Split and insert
			if not content_parts:
				log.debug("No content extracted from %s", filename)
				continue

			char_chunks = convert_Pages_ChunkinChar(content_parts)
			token_chunks = convert_Chunk_Token(char_chunks)

			ids, metadatas = add_meta_data(token_chunks, filename, current_id)
			add_document_to_collection(ids, metadatas, token_chunks, chroma_collection)
			files_processed = True
			current_id += len(token_chunks)

			# Best-effort persist
			try:
				client = vdb_database.get_client_for_collection(chroma_collection)
				if client is not None:
					if hasattr(client, "persist"):
						try:
							client.persist()
						except Exception:
							log.debug("client.persist() failed (non-fatal)")
			except Exception:
				pass

		except (FileNotFoundError, PackageNotFoundError, UnicodeDecodeError) as e:
			log.exception("Failed to load document %s", file_path)
			error_messages.append(str(e))
		except Exception as e:
			log.exception("Unhandled error while processing %s", file_path)
			error_messages.append(str(e))

	if not files_processed and error_messages:
		log.error("No files were processed; errors: %s", error_messages)

	return files_processed, error_messages


# New: load_knowledge_base -> open-only helper (keeps behavior simple)
def load_knowledge_base(collection_name: str, cfg: Optional[dict] = None) -> Tuple[Optional[object], vdb_database.ChromaDBStatus]:
	"""Open an existing persistent ChromaDB collection. Do NOT create paths or ingest."""
	if cfg is None:
		cfg = load_config() or {}
	if not isinstance(cfg, dict):
		cfg = {}
	vcfg = cfg.get("vector_db", {}) if isinstance(cfg, dict) else {}

	resolved = vcfg.get("chromaDB_path")
	if not isinstance(resolved, str) or not resolved.strip():
		log.error("load_knowledge_base requires a persistent chromaDB_path in config.")
		return None, vdb_database.ChromaDBStatus.ERROR

	abs_path = os.path.abspath(resolved)
	if not os.path.isdir(abs_path):
		# Open-only: do not create the directory
		return None, vdb_database.ChromaDBStatus.MISSING_PERSISTENT

	try:
		ret = vdb_database.create_chroma_client(collection_name=collection_name, chromaDB_path=abs_path, create_new=False, config=cfg)
	except Exception:
		log.exception("create_chroma_client failed during load_knowledge_base")
		return None, vdb_database.ChromaDBStatus.ERROR

	# Normalize return shapes
	try:
		if isinstance(ret, tuple) and len(ret) == 3:
			_, collection, status = ret
		elif isinstance(ret, tuple) and len(ret) == 2:
			collection, status = ret
		else:
			collection, status = ret
	except Exception:
		return None, vdb_database.ChromaDBStatus.ERROR

	if status != vdb_database.ChromaDBStatus.OK:
		return None, status

	return collection, status


# NEW: simplified build_knowledge_base matching run.py usage (no legacy branches)
def build_knowledge_base(collection_name: str, document_directory_path: Optional[str] = None, add_documents: bool = False, chromaDB_path: Optional[str] = None, cfg: Optional[dict] = None, overwrite: bool = False) -> Tuple[Optional[object], vdb_database.ChromaDBStatus]:
	"""Create (or open) a persistent ChromaDB collection and optionally ingest documents.

	- collection_name: name of the collection.
	- document_directory_path: path to documents to ingest.
	- add_documents: if True, ingest documents from document_directory_path.
	- chromaDB_path: optional override for storage path; if None, use config or default ./chromaDB.
	- overwrite: if collection exists and overwrite is False, returns ALREADY_EXISTS.
	"""
	# Validate inputs for ingestion
	if add_documents and not document_directory_path:
		log.error("add_documents=True but no document_directory_path provided")
		return None, vdb_database.ChromaDBStatus.ERROR

	# Load config
	if cfg is None:
		cfg = load_config() or {}
	if not isinstance(cfg, dict):
		cfg = {}
	vcfg = cfg.get('vector_db', {}) if isinstance(cfg, dict) else {}

	# Resolve chromaDB path: explicit override > config > default
	resolved = chromaDB_path if chromaDB_path is not None else vcfg.get('chromaDB_path')
	if not isinstance(resolved, str) or not resolved.strip():
		resolved = os.path.join(os.getcwd(), "chromaDB")
		log.info("No chromaDB_path configured; using default: %s", resolved)

	abs_path = os.path.abspath(resolved)
	# Ensure persistent path exists
	try:
		os.makedirs(abs_path, exist_ok=True)
	except Exception:
		log.exception("Failed to create chromaDB directory: %s", abs_path)
		return None, vdb_database.ChromaDBStatus.ERROR

	# Ask DB factory to create/open the collection (create_new=True requests creation)
	try:
		ret = vdb_database.create_chroma_client(collection_name=collection_name, chromaDB_path=abs_path, create_new=True, config=cfg)
	except Exception:
		log.exception("create_chroma_client failed in build_knowledge_base")
		return None, vdb_database.ChromaDBStatus.ERROR

	# Normalize return
	try:
		if isinstance(ret, tuple) and len(ret) == 3:
			_, collection, status = ret
		elif isinstance(ret, tuple) and len(ret) == 2:
			collection, status = ret
		else:
			collection, status = ret
	except Exception:
		return None, vdb_database.ChromaDBStatus.ERROR

	# If collection already exists and overwrite not allowed -> ALREADY_EXISTS
	if status == vdb_database.ChromaDBStatus.ALREADY_EXISTS and not overwrite:
		log.error("Collection already exists: %s", collection_name)
		return None, vdb_database.ChromaDBStatus.ALREADY_EXISTS

	# If creation succeeded and ingestion requested -> ingest
	if add_documents and collection is not None:
		files_processed, errors = load_and_add_documents(collection, document_directory_path, cfg)
		if not files_processed:
			log.error("Ingestion failed or no files processed for %s; errors: %s", document_directory_path, errors)
			return collection, vdb_database.ChromaDBStatus.ERROR

	# Return collection and its status
	return collection, status