import os
from rag_kmk import CONFIG
from rag_kmk.knowledge_base.text_splitter import convert_Pages_ChunkinChar, convert_Chunk_Token, add_meta_data, add_document_to_collection
from rag_kmk.vector_db import create_chroma_client
from rag_kmk.vector_db.database import ChromaDBStatus  # Add this import
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker
from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption, InputFormat
from docling.backend.docling_parse_v2_backend import DoclingParseV2DocumentBackend

from transformers import AutoTokenizer
import time



def build_knowledge_base(document_directory_path=None, chromaDB_path=None):


    EMBED_MODEL_ID = CONFIG['vector_db']['embedding_model']  
    MAX_TOKENS = CONFIG['vector_db']['tokens_per_chunk']  

    tokenizer = AutoTokenizer.from_pretrained(EMBED_MODEL_ID)

    chunker = HybridChunker(
        tokenizer=tokenizer,  # instance or model name, defaults to "sentence-transformers/all-MiniLM-L6-v2"
        max_tokens=MAX_TOKENS,  # optional, by default derived from `tokenizer`
        merge_peers=True,  # optional, defaults to True
    )

    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False # pick what you need
    pipeline_options.do_table_structure = False # pick what you need

    doc_converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options, backend=DoclingParseV2DocumentBackend)  # switch to beta PDF backend
            }
    )


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



    for filename in os.listdir(document_directory_path):
        file_path = os.path.join(document_directory_path, filename)
        file_extension = os.path.splitext(filename)[1]
        
        print(f"\nProcessing file: {filename}")


        if file_extension in CONFIG['supported_file_types']:
            try:
                start_time = time.time()
                print(f'\tLoading document from {file_path}...')
                doc = doc_converter.convert(file_path).document
                conversion_time = time.time() - start_time
                print(f'\tDocument loaded successfully from {file_path} in {conversion_time:.2f} seconds')
                
                chunking_start = time.time()
                chunk_iter = chunker.chunk(dl_doc=doc)
                chunks = list(chunk_iter)
                chunking_time = time.time() - chunking_start
                print(f"\tDocument chunked into {len(chunks)} chunks in {chunking_time:.2f} seconds")
                
                ids=[]
                metadatas=[]
                text_chunksinTokens = []
                
                tokenization_start = time.time()
                for i, chunk in enumerate(chunks):
                    print(f"=== {i} ===")
                    txt_tokens = len(tokenizer.tokenize(chunk.text))
                    #print(f"\t\tchunk.text ({txt_tokens} tokens):\n{chunk.text!r}")
                    ser_txt = chunker.contextualize(chunk=chunk)
                    ser_tokens = len(tokenizer.tokenize(ser_txt))
                    print(f"\t\tchunker.contextualize(chunk) ({ser_tokens} tokens):\n{ser_txt!r}")
                    print()
                    ids.append(str(i+current_id))
                    text_chunksinTokens.append(chunker.contextualize(chunk=chunk))
                    metadatas.append( {                        
                        #"headings": chunk.meta.headings,
                        "document": chunk.meta.origin.filename,
                        #"file_uri": chunk.meta.origin.uri
                    })
                tokenization_time = time.time() - tokenization_start
                print(f"\tTokenization and metadata preparation completed in {tokenization_time:.2f} seconds")

                storage_start = time.time()
                current_id += len(text_chunksinTokens)
                chroma_collection = add_document_to_collection(ids, metadatas, text_chunksinTokens, chroma_collection)
                storage_time = time.time() - storage_start
                
                total_time = time.time() - start_time
                print(f"\nDocument {filename} processing summary:")
                print(f"- Document conversion: {conversion_time:.2f} seconds")
                print(f"- Chunking: {chunking_time:.2f} seconds")
                print(f"- Tokenization and metadata: {tokenization_time:.2f} seconds")
                print(f"- ChromaDB storage: {storage_time:.2f} seconds")
                print(f"- Total processing time: {total_time:.2f} seconds")
                print(f"- Added {len(chunks)} chunks to collection")
                print(f"- Current collection size: {chroma_collection.count()} chunks\n")

            except Exception as e:
                
                print(f'\nFailed to load document from {file_path}: {e}')
                continue

        else:
            print(f'\nSkipping unsupported file type: {file_path}')

    print(f'\nKnowledge Based populated by a total number of {chroma_collection.count()} document chunks from {document_directory_path}.')


    return chroma_collection, chromaDB_status

