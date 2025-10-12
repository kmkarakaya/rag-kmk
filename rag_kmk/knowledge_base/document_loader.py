import os
import fitz  # PyMuPDF
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

	# Helper to extract vector DB defaults
	db_cfg = cfg.get('vector_db', {}) if isinstance(cfg, dict) else {}
	collection_name = db_cfg.get('collection_name')
	sentence_transformer_model = db_cfg.get('embedding_model')

	# Three explicit behaviors depending on parameters (or config fallback):
	# 1) chromaDB_path provided and document_directory_path provided =>
	#    load persistent collection and add new documents
	# 2) chromaDB_path provided and document_directory_path is None =>
	#    load persistent collection only (do not add documents)
	# 3) chromaDB_path is None and document_directory_path provided =>
	#    create an in-memory collection and add documents

	chroma_client = chroma_collection = chromaDB_status = None

	if chromaDB_path is not None:
		# Persistent mode (either with or without adding documents)
		chroma_client, chroma_collection, chromaDB_status = vdb_database.create_chroma_client(
			chromaDB_path=chromaDB_path,
			collection_name=collection_name,
			sentence_transformer_model=sentence_transformer_model,
		)
		if document_directory_path is None:
			# Mode 2: persistent-only
			print(f"***** 👍 Only a permanent ChromaDB loaded: {getattr(chromaDB_status, 'value', chromaDB_status)} *****")
			if chroma_collection is None:
				print("Error: chroma collection not available; aborting knowledge base build")
				return None, chromaDB_status
			return chroma_collection, chromaDB_status
		else:
			# Mode 1: persistent + add documents
			print(f"***** 👍 Permanent ChromaDB loaded and new documents will be added: {getattr(chromaDB_status, 'value', chromaDB_status)} *****")
			if chroma_collection is None:
				print("Error: chroma collection not available; aborting knowledge base build")
				return None, chromaDB_status

	elif document_directory_path is not None:
		# Mode 3: in-memory + add documents
		chroma_client, chroma_collection, chromaDB_status = vdb_database.create_chroma_client(
			chromaDB_path=None,
			collection_name=collection_name,
			sentence_transformer_model=sentence_transformer_model,
		)
		print(f"***** 👍 New in-memory ChromaDB created and documents will be added from: {document_directory_path} *****")
		if chroma_collection is None:
			print("Error: chroma collection not available; aborting knowledge base build")
			return None, chromaDB_status

	else:
		# Neither persistent nor document directory provided: nothing to do.
		print("No chroma collection available; nothing to do.")
		return None, None

	current_id = chroma_collection.count()
	print(f"Current Number of Document Chunks in Vector DB : {current_id}")

	# Validate directory
	if not os.path.isdir(document_directory_path):
		raise ValueError(f"Invalid directory path: '{document_directory_path}'. Please provide a valid directory.")

	files_processed = False
	error_messages = []

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
								print(f'\nText document {filename} loaded successfully from {file_path}')
							else:
								print(f"\nWarning: Skipping empty or unreadable .txt file: {filename}")
					except FileNotFoundError:
						print(f"Error: File not found: {file_path}")
						error_messages.append(f"File not found: {file_path}")
					except UnicodeDecodeError:
						print(f"Error: Could not decode file {file_path} with UTF-8. Try specifying a different encoding.")
						error_messages.append(f"Could not decode file {file_path} with UTF-8.")
					except Exception as e:
						print(f"An unexpected error occurred while processing {file_path}: {e}")
						error_messages.append(f"An unexpected error occurred while processing {file_path}: {e}")

				elif file_extension == '.pdf':
					with fitz.open(file_path) as doc:
						text = ''
						for page in doc:
							text += page.get_text()
						document.append(text)
					print(f'\nPDF document {filename} loaded successfully from {file_path}')

				elif file_extension == '.docx':
					try:
						# Import docx2txt lazily so tests and other imports don't require it at module-import time
						try:
							import docx2txt
						except ImportError:
							print(f"Error: docx2txt library not found. Please install it using 'pip install docx2txt'. Skipping '{filename}'.")
							continue
						text = docx2txt.process(file_path)
						document.append(text)
						if not text:
							raise ValueError(f"No text extracted from {filename}")
						print(f"\nDOCX document '{filename}' loaded successfully from '{file_path}'. Text length: {len(text)} characters.")
					except Exception as e:
						error_messages.append(f"Failed to load document '{filename}': {e}")
						print(f"\nFailed to load document from '{file_path}': {e}")
						continue

				# Splitting and storing
				text_chunksinChar = convert_Pages_ChunkinChar(document)
				text_chunksinTokens = convert_Chunk_Token(text_chunksinChar)
				ids, metadatas = add_meta_data(text_chunksinTokens, filename, current_id)
				current_id += len(text_chunksinTokens)
				chroma_collection = add_document_to_collection(ids, metadatas, text_chunksinTokens, chroma_collection)
				files_processed = True
				print(f"Document {filename} added to the collection")
				print(f"Current number of document chunks in Vector DB: {chroma_collection.count()} ")
			except (FileNotFoundError, fitz.EmptyFileError, PackageNotFoundError, UnicodeDecodeError) as e:
				error_messages.append(f"Failed to load document '{filename}': {e}.  Try specifying encoding.")
				print(f'\nFailed to load document from {file_path}: {e}')
				continue
			except Exception as e:
				error_messages.append(f"Failed to load document '{filename}': {e}")
				print(f'\nFailed to load document from {file_path}: {e}')
				continue

		else:
			print(f'\nSkipping unsupported file type: {file_path}')

	print(f'\nKnowledge Based populated by a total number of {chroma_collection.count()} document chunks from {document_directory_path}.')
	if not files_processed:
		print(f"\nNo files were processed successfully from the directory: {document_directory_path}.")
		print("Please check the directory path and the file types.")
		return None
	if error_messages:
		print("\nErrors encountered during processing:")
		for msg in error_messages:
			print(msg)
	return chroma_collection, chromaDB_status


__all__ = ['build_knowledge_base']

