# Usage

To use rag-kmk in a project:

```
from rag_kmk.knowledge_base import build_knowledge_base   
from rag_kmk.chat_flow import RAG_LLM, run_rag_pipeline  

# Load the documents
knowledge_base= build_knowledge_base(r'.\tests\sample_documents')     
run_rag_pipeline(RAG_LLM,knowledge_base)
```

