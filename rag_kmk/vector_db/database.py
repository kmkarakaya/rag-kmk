from rag_kmk import CONFIG 
from chromadb import Client, PersistentClient
from chromadb.utils import embedding_functions
import json
from enum import Enum

# Define status enum
class ChromaDBStatus(Enum):
    EXISTING_PERMANENT = "Existing permenant collection found"
    NEW_PERMANENT = "New permenant collection created"
    NEW_MEMORY = "New in-memory collection created"
    FAILED_MEMORY = "New in-memory collection not created"
    
def create_chroma_client(chromaDB_path=CONFIG["vector_db"]["chromaDB_path"], 
                         collection_name=CONFIG["vector_db"]["collection_name"], 
                         sentence_transformer_model=CONFIG["vector_db"]["embedding_model"]
                         ):
    status = None
    embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=sentence_transformer_model,
        device="cpu"  # Force CPU usage
    )
    
    if chromaDB_path is not None:
        print("Trying to access collection at ", chromaDB_path, " using Persistent Client")
        
        try:
            chroma_client = PersistentClient(path=chromaDB_path)
            chroma_collection = chroma_client.get_collection(
                collection_name,
                embedding_function=embedding_function)
            print(f"\tCollection {collection_name} found and uploaded!")
            status = ChromaDBStatus.EXISTING_PERMANENT
            
        except:
            print(f"\tCollection {collection_name} does not exist")
            print("\tCreating a new collection")
            chroma_collection = chroma_client.create_collection(
                collection_name,
                embedding_function=embedding_function)
            print(f"\tCollection {collection_name} was created succesfully")
            status = ChromaDBStatus.NEW_PERMANENT

    else:
        print("Using in-memory Client:")
        print("\tCreating a new collection")
        chroma_client = Client()
        try:
            chroma_collection = chroma_client.create_collection(
                collection_name,
                embedding_function=embedding_function)
            status = ChromaDBStatus.NEW_MEMORY
            print(f"\tCollection {collection_name} was created succesfully")
        except:
            print(f"\tCollection {collection_name} was not created")
            status = ChromaDBStatus.FAILED_MEMORY
            return None, None, status
    
    return chroma_client, chroma_collection, status


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
  print(json.dumps(summary, indent=2))
  return json.dumps(summary, indent=2)
