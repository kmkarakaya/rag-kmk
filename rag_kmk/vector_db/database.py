from rag_kmk import CONFIG 
from chromadb import Client, PersistentClient
from chromadb.utils import embedding_functions

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
  summary = [] # Initialize summary as a list
  print("Summarizing the collection...")
  # Verify collection properties
  print(f"\t Collection name: {chroma_collection.name}")  # Access the name attribute directly
  print(f"\t Number of document chunks in collection: {chroma_collection.count()}")
  summary.append(f"Collection name: {chroma_collection.name}") # Append to the list
  summary.append(f"Number of document chunks in collection: {chroma_collection.count()}")
  # Print distinct metadata "document" for each chunk in the collection
  print("\t Distinct 'document' metadata in the collection:")
  distinct_documents = set()  # Use a set to store unique document names

  # Iterate over chunks in the collection
  for chunk_id in range(chroma_collection.count()):
      metadata = chroma_collection.get([str(chunk_id)])['metadatas'][0]  # Get metadata for the chunk
      document_name = metadata.get("document", "Unknown")  # Get document metadata; default to "Unknown" if not present
      distinct_documents.add(document_name)  # Add document name to set for uniqueness

  # Print all distinct document names
  summary.append("Documents:")
  for document_name in distinct_documents:
      print("\t ",document_name)
      summary.append(document_name) # Append to the list

  print("Collection summarization completed.")

  # Join the list elements into a single string
  summary_string = "\n ".join(summary)
  return summary_string
