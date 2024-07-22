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
    
    '''
    
    chroma_client = PersistentClient(chromaDB_path)

    chroma_collection = chroma_client.get_or_create_collection(collection_name,embedding_function=embedding_function)
'''
   
    return chroma_client, chroma_collection

