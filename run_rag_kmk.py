from rag_kmk.knowledge_base import build_knowledge_base  
from rag_kmk.vector_db import summarize_collection 
from rag_kmk.chat_flow import RAG_LLM, run_rag_pipeline    

def main():
    knowledge_base = build_knowledge_base(r'./tests/sample_documents/')  
    if knowledge_base is None:
        print('No knowledge base created. Exiting')
        return 
    summarize_collection(knowledge_base) 
    run_rag_pipeline(RAG_LLM, knowledge_base)

if __name__ == "__main__":
    main()