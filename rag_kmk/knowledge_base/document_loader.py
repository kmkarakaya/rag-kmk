import os
import logging
from typing import Optional, Tuple
import warnings
import time

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


def load_and_add_documents(chroma_collection, document_directory_path, cfg, **kwargs):
	"""Scan a directory, split found documents and add them to `chroma_collection`.

	Returns (files_processed: bool, errors: list[str]).
	Accepts kwargs for future options (e.g. disable_embeddings) but is backwards compatible.
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

			# print(f"[rag-kmk][doc_loader] file={filename} - starting page->char split", flush=True)
			char_chunks = convert_Pages_ChunkinChar(content_parts)
			# print(f"[rag-kmk][doc_loader] file={filename} - char_chunks={len(char_chunks)}", flush=True)

			# print(f"[rag-kmk][doc_loader] file={filename} - starting tokenization (convert_Chunk_Token)", flush=True)
			start_token_ts = time.perf_counter()
			token_chunks = convert_Chunk_Token(char_chunks)
			token_dur = time.perf_counter() - start_token_ts
			# print(f"[rag-kmk][doc_loader] file={filename} - token_chunks={len(token_chunks)} tokenization_time={token_dur:.3f}s", flush=True)

			ids, metadatas = add_meta_data(token_chunks, filename, current_id)

			# GUARANTEED PRINT: show handoff to add step (helps locate stall)
			print(f"[rag-kmk][doc_loader] HANDOFF to add_document_to_collection: file={filename} chunks={len(token_chunks)}", flush=True)
			# Lightweight debug: single info log before adding (embedding may happen here)
			disable_emb = bool(kwargs.get('disable_embeddings', False))
			log.info(
				"Adding %d chunks to collection %r (filename=%s). disable_embeddings=%s.",
				len(token_chunks),
				getattr(chroma_collection, 'name', '<unknown>'),
				filename,
				disable_emb,
			)

			# Perform add (unchanged)
			try:
				start_add_ts = time.perf_counter()
				add_document_to_collection(ids, metadatas, token_chunks, chroma_collection, **kwargs)
				add_dur = time.perf_counter() - start_add_ts
				print(f"[rag-kmk][doc_loader] add_document_to_collection completed for {filename} duration={add_dur:.3f}s", flush=True)
			except Exception as e:
				log.exception("add_document_to_collection failed for %s: %s", filename, e)
				error_messages.append(str(e))
				continue

			# Lightweight debug: log after add completes
			log.info("Finished adding %d chunks for %s", len(token_chunks), filename)

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