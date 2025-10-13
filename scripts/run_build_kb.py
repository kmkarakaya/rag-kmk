import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from rag_kmk.knowledge_base import build_knowledge_base

kb,status = build_knowledge_base(document_directory_path=r'.\\tests\\sample_documents', chromaDB_path=r'.\\chromaDB')
print('returned status:', status)
print('kb is None?', kb is None)
