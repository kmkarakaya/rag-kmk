from  rag_kmk import CONFIG
from rag_kmk.knowledge_base import build_knowledge_base   
from rag_kmk.vector_db import summarize_collection, retrieve_chunks, show_results
from rag_kmk.chat_flow import generateAnswer, generate_LLM_answer, RAG_LLM, run_rag_pipeline  


def main():
       
    '''
    Load the documents from the sample_documents folder and print the first 200 characters of each document.        

    '''
    

    # Load the documents
    knowledge_base= build_knowledge_base(r'.\tests\sample_documents')     

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