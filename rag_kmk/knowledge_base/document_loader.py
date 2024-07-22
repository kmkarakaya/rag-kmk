import os
import fitz  # PyMuPDF
from docx import Document
from rag_kmk import CONFIG
from rag_kmk.knowledge_base.text_splitter import convert_Pages_ChunkinChar, convert_Chunk_Token, add_meta_data, add_document_to_collection
from rag_kmk.vector_db import create_chroma_client



def build_knowledge_base(document_directory_path):
    """
    Loads document from a specified directory. Supported file types are defined in CONFIG['supported_file_types'].
    Currently supports .txt, .pdf, and .docx files.

    Parameters:
    - directory_path (str): The path to the directory containing the document to be loaded.

    Returns:
    - list: A list of document contents as strings.
    """

    #chroma_client, chroma_collection = create_chroma_client(CONFIG["vector_db"]["chromaDB_path"])
    chroma_client, chroma_collection = create_chroma_client()
    
    current_id = chroma_collection.count()
    print(f"Current Number of Document Chunks in Vector DB : {current_id}")


    if not os.path.isdir(document_directory_path):
        print(f'{document_directory_path} is not a directory.')
        return
        

    for filename in os.listdir(document_directory_path):
        file_path = os.path.join(document_directory_path, filename)
        file_extension = os.path.splitext(filename)[1]
        
        document = []

        if file_extension in CONFIG['supported_file_types']:
            try:
                if file_extension == '.txt':
                    with open(file_path, 'r') as file:
                        document = file.read()
                    document.append(document)
                    print(f'\nText document {filename} loaded successfully from {file_path}')
                elif file_extension == '.pdf':
                    with fitz.open(file_path) as doc:
                        text = ''
                        for page in doc:
                            text += page.get_text()
                    document.append(text)
                    print(f'\nPDF document {filename} loaded successfully from {file_path}')
                elif file_extension == '.docx':
                    doc = Document(file_path)
                    text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
                    document.append(text)
                    print(f'\nDOCX document {filename} loaded successfully from {file_path}')

                print(f"Processing the document {filename} to add to the {chroma_collection.name} collection")
                print(f"Current number of document chunks in Vector DB: {chroma_collection.count()} ")
                text_chunksinChar = convert_Pages_ChunkinChar(document)
                text_chunksinTokens = convert_Chunk_Token(text_chunksinChar)
                ids,metadatas = add_meta_data(text_chunksinTokens,filename, current_id)
                current_id = current_id + len(text_chunksinTokens)
                chroma_collection = add_document_to_collection(ids, metadatas, text_chunksinTokens, chroma_collection)
                print(f"Document {filename} added to the collection")
                print(f"Current number of document chunks in Vector DB: {chroma_collection.count()} ")
                

                
            except Exception as e:
                print(f'\nFailed to load document from {file_path}: {e}')
        else:
            print(f'\nSkipping unsupported file type: {file_path}')

    print(f'\nKnowledge Based populated by a total number of {chroma_collection.count()} document chunks from {document_directory_path}.')
    return chroma_collection
    