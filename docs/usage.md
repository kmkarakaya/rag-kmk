# Usage

To use rag-kmk in a project:

```
#pip install rag-kmk
from rag_kmk.knowledge_base import build_knowledge_base  
from rag_kmk.vector_db import summarize_collection 
from rag_kmk.chat_flow import RAG_LLM, run_rag_pipeline    

def main():
    knowledge_base= build_knowledge_base(r'.\files')  
    summarize_collection(knowledge_base) 
    run_rag_pipeline(RAG_LLM,knowledge_base)

if __name__ == "__main__":
    main()
```

