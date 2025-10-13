import os
import fitz  # PyMuPDF
import logging
from docx.opc.exceptions import PackageNotFoundError
import rag_kmk
from rag_kmk.knowledge_base.text_splitter import (
	convert_Pages_ChunkinChar,
	convert_Chunk_Token,
	add_meta_data,
	add_document_to_collection,
)
import rag_kmk.vector_db.database as vdb_database
from rag_kmk.vector_db.database import ChromaDBStatus


log = logging.getLogger(__name__)


def load_and_add_documents(chroma_collection, document_directory_path, cfg):
	"""Scans a directory for documents, processes them, and adds them to the collection."""
	current_id = chroma_collection.count()
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
					text_chunksinChar = convert_Pages_ChunkinChar(document)
					text_chunksinTokens = convert_Chunk_Token(text_chunksinChar)
					ids, metadatas = add_meta_data(text_chunksinTokens, filename, current_id)
					current_id += len(text_chunksinTokens)
					add_document_to_collection(ids, metadatas, text_chunksinTokens, chroma_collection)
					files_processed = True
					log.debug(f"Document {filename} added to the collection.")
					log.debug(f"Current number of document chunks in Vector DB: {chroma_collection.count()}")
			except (FileNotFoundError, fitz.EmptyFileError, PackageNotFoundError, UnicodeDecodeError) as e:
				error_messages.append(f"Failed to load document '{filename}': {e}.  Try specifying encoding.")
				log.exception(f'Failed to load document from {file_path}')
				continue
			except Exception as e:
				error_messages.append(f"Failed to load document '{filename}': {e}")
				log.exception(f'Failed to load document from {file_path}')
				continue

		else:
			log.debug(f'Skipping unsupported file type: {file_path}')
	
	return files_processed, error_messages


def build_knowledge_base(document_directory_path=None, chromaDB_path=None, config=None):
	"""Build or load the knowledge base into Chroma.

	This is the project's single document loader. It supports .txt, .pdf,
	and .docx files. It creates either an in-memory Chroma collection or
	connects to a persistent Chroma DB, then converts documents to text,
	splits them into chunks, and inserts embeddings via the vector DB
	helper functions.

	Returns:
		(chroma_collection, chromaDB_status)
	"""
	# Resolve config (prefer explicit param, fallback to module-level CONFIG)
	cfg = config if config is not None else getattr(rag_kmk, 'CONFIG', {}) or {}

	log.debug(f"Entering build_knowledge_base with document_directory_path='{document_directory_path}' and chromaDB_path='{chromaDB_path}'")

	# Three explicit behaviors depending on parameters:
	# 1) chromaDB_path provided and document_directory_path provided =>
	#    load persistent collection and add new documents.
	# 2) chromaDB_path provided and document_directory_path is None =>
	#    load persistent collection only (do not add documents).
	# 3) chromaDB_path is None and document_directory_path provided =>
	#    create an in-memory collection and add documents.

	# If neither path is provided, there's nothing to do.
	if not chromaDB_path and not document_directory_path:
		log.warning("Neither chromaDB_path nor document_directory_path provided. Nothing to do.")
		return None, None

	# Helper to extract vector DB defaults
	db_cfg = cfg.get('vector_db', {}) if isinstance(cfg, dict) else {}
	collection_name = db_cfg.get('collection_name')
	sentence_transformer_model = db_cfg.get('embedding_model')

	# Step 1: Get or create the ChromaDB collection.
	# The create_chroma_client function handles both persistent (with path) and in-memory (path is None).
	chroma_client, chroma_collection, chromaDB_status = vdb_database.create_chroma_client(
		chromaDB_path=chromaDB_path,
		collection_name=collection_name,
		sentence_transformer_model=sentence_transformer_model,
	)

	# Sanity check: if a persistent path was requested, we should not get an in-memory collection.
	if chromaDB_path and chromaDB_status == ChromaDBStatus.NEW_MEMORY:
		raise RuntimeError(
			"create_chroma_client returned an in-memory collection while a persistent chromaDB_path was requested."
		)

	if chroma_collection is None:
		log.error("Chroma collection not available; aborting knowledge base build.")
		return None, chromaDB_status

	# Step 2: If a document directory is provided, load and add documents.
	if not document_directory_path:
		log.debug("No document directory provided. Skipping document loading.")
		return chroma_collection, chromaDB_status

	files_processed, error_messages = load_and_add_documents(
		chroma_collection, document_directory_path, cfg
	)

	log.info(f'Knowledge Base populated by a total number of {chroma_collection.count()} document chunks from {document_directory_path}.')
	if not files_processed:
		log.warning(f"No files were processed successfully from the directory: {document_directory_path}.")
		log.warning("Please check the directory path and the file types.")
		return None, chromaDB_status  # Return status with collection even if no files were added
	if error_messages:
		log.error("Errors encountered during processing:")
		for msg in error_messages:
			log.error(msg)
	return chroma_collection, chromaDB_status


__all__ = ['build_knowledge_base', 'load_and_add_documents']

