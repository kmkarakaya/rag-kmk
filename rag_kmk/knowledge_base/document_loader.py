import os
import fitz  # PyMuPDF
#from docx import Document
import docx2txt
from docx.opc.exceptions import PackageNotFoundError
from rag_kmk import CONFIG
from rag_kmk.knowledge_base.text_splitter import convert_Pages_ChunkinChar, convert_Chunk_Token, add_meta_data, add_document_to_collection
from rag_kmk.vector_db import create_chroma_client
from rag_kmk.vector_db.database import ChromaDBStatus  # Add this import




def build_knowledge_base(document_directory_path=None, chromaDB_path=None):
    # if the user ONLY wants to load a permenant chromaDB collection, then the document_directory_path should be None
    # and the chromaDB_path should be provided. In this case, we will not load any documents from the directory. 
    if chromaDB_path is not None and document_directory_path is None:
        chroma_client, chroma_collection, chromaDB_status=create_chroma_client(chromaDB_path=chromaDB_path)
        print(f"***** 👍 Only a permanent ChromaDB loaded: {chromaDB_status.value} *****")
        return chroma_collection, chromaDB_status
    
    # if the user wants to load a permenant chromaDB collection and also add new documents from the directory, 
    # then both the paths should be provided.
    if chromaDB_path is not None and document_directory_path is not None:
        chroma_client, chroma_collection, chromaDB_status=create_chroma_client(chromaDB_path=chromaDB_path)
        print(f"***** 👍 Permanent ChromaDB loaded and new documents added: {chromaDB_status.value} *****")
    
    # if the user wants to create a new in-memory chromaDB collection and also add new documents from the directory,
    if chromaDB_path is None and document_directory_path is not None:
        chroma_client, chroma_collection, chromaDB_status = create_chroma_client(chromaDB_path=None)
        print(f"***** 👍 New in-memory ChromaDB created and documents will be added from: {document_directory_path} *****")
    
    
    current_id = chroma_collection.count()
    print(f"Current Number of Document Chunks in Vector DB : {current_id}")

    # Check if the provided path is a directory.  If not, raise a ValueError with a helpful message.
    if not os.path.isdir(document_directory_path):
        raise ValueError(f"Invalid directory path: '{document_directory_path}'. Please provide a valid directory.")

    files_processed = False # Flag to track if any files were processed successfully
    error_messages = [] # Collect error messages for all failed files

    for filename in os.listdir(document_directory_path):
        file_path = os.path.join(document_directory_path, filename)
        file_extension = os.path.splitext(filename)[1]
        document = []

        if file_extension in CONFIG['supported_file_types']:
            try:
                if file_extension == '.txt':
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                            text = ""
                            chunk_size = 1024 * 1024  # 1MB chunks
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
                        text = docx2txt.process(file_path)
                        document.append(text)
                        if not text:
                            raise ValueError(f"No text extracted from {filename}")
                        print(f"\nDOCX document '{filename}' loaded successfully from '{file_path}'. Text length: {len(text)} characters.")
                    except ImportError:
                        print(f"Error: docx2txt library not found. Please install it using 'pip install docx2txt'. Skipping '{filename}'.")
                        continue
                    except Exception as e:
                        error_messages.append(f"Failed to load document '{filename}': {e}")
                        print(f"\nFailed to load document from '{file_path}': {e}")
                        continue

                text_chunksinChar = convert_Pages_ChunkinChar(document)
                text_chunksinTokens = convert_Chunk_Token(text_chunksinChar)
                ids, metadatas = add_meta_data(text_chunksinTokens, filename, current_id)
                current_id += len(text_chunksinTokens)
                chroma_collection = add_document_to_collection(ids, metadatas, text_chunksinTokens, chroma_collection)
                files_processed = True # Set flag if processing was successful
                print(f"Document {filename} added to the collection")
                print(f"Current number of document chunks in Vector DB: {chroma_collection.count()} ")
            except (FileNotFoundError, fitz.EmptyFileError, PackageNotFoundError, UnicodeDecodeError) as e: #Catch UnicodeDecodeError
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

