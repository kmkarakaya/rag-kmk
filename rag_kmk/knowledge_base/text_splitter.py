from rag_kmk import CONFIG
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.text_splitter import SentenceTransformersTokenTextSplitter


def convert_Pages_ChunkinChar(text_in_pages, chunk_size=CONFIG["knowledge_base"]["chunk_size"], 
                              chunk_overlap=CONFIG["knowledge_base"]["chunk_overlap"]):
    character_splitter = RecursiveCharacterTextSplitter(separators=["\n\n", "\n", ". ", " ", ""],  
                                                        chunk_size=chunk_size, 
                                                        chunk_overlap=chunk_overlap)
    character_split_texts = character_splitter.split_text('\n\n'.join(text_in_pages))
    print(f"Total number of chunks (document splited by max char = {chunk_size}): {len(character_split_texts)}")
    return character_split_texts

def convert_Chunk_Token(text_chunksinChar,
                        sentence_transformer_model=CONFIG["vector_db"]["embedding_model"], 
                        chunk_overlap=CONFIG["knowledge_base"]["chunk_overlap"],
                        tokens_per_chunk=CONFIG["vector_db"]["tokens_per_chunk"]):
    token_splitter = SentenceTransformersTokenTextSplitter(
        chunk_overlap=chunk_overlap,
        model_name=sentence_transformer_model,
        tokens_per_chunk=tokens_per_chunk)
    
    text_chunksinTokens = []
    for text in text_chunksinChar:
        text_chunksinTokens += token_splitter.split_text(text)
        
    print(f"Total number of chunks (document splited by 128 tokens per chunk): {len(text_chunksinTokens)}")
    return text_chunksinTokens

def add_document_to_collection(ids, metadatas, text_chunksinTokens, chroma_collection):
  print("Before inserting, the size of the collection: ", chroma_collection.count())
  #print(f"{metadatas}")
  chroma_collection.add(ids=ids, metadatas=metadatas, documents=text_chunksinTokens)
  print("After inserting, the size of the collection: ", chroma_collection.count())
  return chroma_collection


def add_meta_data(text_chunksinTokens, title, initial_id,  category=CONFIG["vector_db"]["category"]):
  ids = [str(i+initial_id) for i in range(len(text_chunksinTokens))]
  metadata = {
      'document': title,
      'category': category
  }
  metadatas = [ metadata for i in range(len(text_chunksinTokens))]
  return ids, metadatas

