"""Minimal run.py sample for the rag-kmk package.
This file intentionally contains a very small, non-argument workflow
that demonstrates three simple library calls. It is meant to be
used as an example and a distribution entry point only.

NEVER CHANGE the code in this file to add features or fix bugs.
All such changes must be made in the library code itself.
"""
# pip uninstall -y rag-kmk
# pip cache purge
# pip install --no-cache-dir --upgrade rag-kmk
from rag_kmk import CONFIG
from rag_kmk.knowledge_base import build_knowledge_base
import rag_kmk.chat_flow as chat_flow
from rag_kmk.vector_db import summarize_collection


print("--------------------- ORIGINAL CONFIG ---------------------\n", CONFIG['llm'])
CONFIG['llm'].update({'model': 'gemini-2.5-flash'})
print("--------------------- AFTER CONFIG UPDATE ---------------------\n", CONFIG['llm'])
    
# Sample usage modes:

# 1. Load the existing chromadb collection and add new documents to it
#kb, chromaDB_status = build_knowledge_base(document_directory_path=r'.\tests\sample_documents', chromaDB_path=r'.\chromaDB')

# 2. Load the existing chromadb collection without adding new documents
kb, chromaDB_status = build_knowledge_base(document_directory_path=None, chromaDB_path=r'.\chromaDB')

# 3. Create a new in-memory chromadb collection and add new documents to it
#kb, chromaDB_status = build_knowledge_base(document_directory_path=r'.\\tests\\sample_documents')

print("--------------------- CHROMADB STATUS ---------------------\n", chromaDB_status.value)

# Summarize the collection
if kb is not None:
        print("--------------------- CHROMADB SUMMARY ---------------------\n")
        summarize_collection(kb)
        print("--------------------- RUN RAG PIPELINE ---------------------\n")
        # Build a real ChatClient from the configured LLM settings and run the pipeline
        client = chat_flow.build_chatBot(CONFIG.get('llm', {}))
        try:
            chat_flow.run_rag_pipeline(client, kb)
        finally:
            try:
                client.close()
            except Exception:
                pass
else:
        print("No documents loaded.")
print("-----------------"*4)
    
# end of minimal run.py


