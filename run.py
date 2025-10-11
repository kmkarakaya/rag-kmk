#pip install rag-kmk
# ensure that you have a directory ./files with some documents in it.
from  rag_kmk import CONFIG
from rag_kmk.knowledge_base import build_knowledge_base   
from rag_kmk.vector_db import summarize_collection, retrieve_chunks, show_results
from rag_kmk.chat_flow import generateAnswer, generate_LLM_answer, RAG_LLM, run_rag_pipeline, build_chatBot


def main():
    print("--------------------- ORIGINAL CONFIG ---------------------\n", CONFIG['llm'])
    CONFIG['llm'].update({'model': 'gemini-2.5-flash'})
    print("--------------------- AFTER CONFIG UPDATE ---------------------\n", CONFIG['llm'])
    
    global RAG_LLM
    RAG_LLM = build_chatBot()
    
    # Load the existing chromadb collection and add new documents to it
    #knowledge_base, chromaDB_status = build_knowledge_base(document_directory_path=r'.\tests\sample_documents', chromaDB_path=r'.\chromaDB')

    # Load the existing chromadb collection without adding new documents
    #knowledge_base, chromaDB_status = build_knowledge_base( chromaDB_path=r'.\chromaDB')

    # Create a new in-memory chromadb collection and add new documents to it
    knowledge_base, chromaDB_status = build_knowledge_base( document_directory_path=r'.\tests\sample_documents')

    print("--------------------- CHROMADB STATUS ---------------------\n", chromaDB_status.value)
    print("-----------------"*4)
    print(CONFIG)    

    print("-----------------"*4)  
    # Summarize the collection
    if knowledge_base:
        summarize_collection(knowledge_base)
        run_rag_pipeline(RAG_LLM,knowledge_base)
    else:
        print("No documents loaded.")
    print("-----------------"*4)
    



if __name__ == "__main__":
    main()
