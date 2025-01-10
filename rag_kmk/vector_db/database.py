from rag_kmk import CONFIG 
from chromadb import Client, PersistentClient
from chromadb.utils import embedding_functions
import json

def create_chroma_client(chromaDB_path=CONFIG["vector_db"]["chromaDB_path"], 
                         collection_name=CONFIG["vector_db"]["collection_name"], 
                         sentence_transformer_model=CONFIG["vector_db"]["embedding_model"]
                         ):
    embedding_function= embedding_functions.SentenceTransformerEmbeddingFunction( model_name=sentence_transformer_model)
    
    if chromaDB_path is not None:
        print("Using Persistent Client with path: ", chromaDB_path)
        chroma_client = PersistentClient(path=chromaDB_path)
    else:
        print("Using in-memory Client")
        chroma_client = Client()

    
    try:
        chroma_collection = chroma_client.get_collection(
        collection_name,
        embedding_function=embedding_function)
        print(f"Collection {collection_name} already exists: deleting it")
        chroma_client.delete_collection(name=collection_name)
    except:
        print(f"Collection {collection_name} does not exist")
        
    
    print("Creating a new collection")
    chroma_collection = chroma_client.create_collection(
        collection_name,

        embedding_function=embedding_function)
    
    return chroma_client, chroma_collection


def summarize_collection(chroma_collection):
  summary = {} # Initialize summary as a dictionary
  summary["collection_name"] = chroma_collection.name
  summary["document_count"] = chroma_collection.count()
  summary["documents"] = []

  distinct_documents = set()
  for chunk_id in range(chroma_collection.count()):
      metadata = chroma_collection.get([str(chunk_id)])['metadatas'][0]
      document_name = metadata.get("document", "Unknown")
      distinct_documents.add(document_name)

  for document_name in distinct_documents:
      summary["documents"].append(document_name)

  return json.dumps(summary, indent=2)
