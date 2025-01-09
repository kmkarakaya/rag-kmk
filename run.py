#pip install rag-kmk
# ensure that you have a directory ./files with some documents in it.
from  rag_kmk import CONFIG
from rag_kmk.knowledge_base import build_knowledge_base   
from rag_kmk.vector_db import summarize_collection, retrieve_chunks, show_results
from rag_kmk.chat_flow import generateAnswer, generate_LLM_answer, RAG_LLM, run_rag_pipeline  


def main():
    print(CONFIG['llm']['model'])
    CONFIG.update({'llm': {'model': 'updated-model-name'}})
    print(CONFIG['llm']['model'])
    # # Load the documents
    # knowledge_base= build_knowledge_base(r'.\tests\sample_documents') 
    # print("-----------------"*4)
    # print(CONFIG)    

    # print("-----------------"*4)  
    # # Summarize the collection
    # if knowledge_base:
    #     summarize_collection(knowledge_base)
    #     run_rag_pipeline(RAG_LLM,knowledge_base)
    # else:
    #     print("No documents loaded.")
    print("-----------------"*4)
    



if __name__ == "__main__":
    main()
