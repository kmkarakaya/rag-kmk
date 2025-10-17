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
from rag_kmk.knowledge_base import document_loader as kb_loader
import rag_kmk.chat_flow as chat_flow
from rag_kmk.vector_db import database as vdb_database
from rag_kmk.vector_db import summarize_collection


print("--------------------- ORIGINAL CONFIG ---------------------\n", CONFIG['llm'])
CONFIG['llm'].update({'model': 'gemini-2.5-flash'})
print("--------------------- AFTER CONFIG UPDATE ---------------------\n", CONFIG['llm'])
    
# Simplified persistent-only usage examples (two fundamental use cases):

# 1) Create a new persistent ChromaDB collection and ingest documents from a folder.
#    Provide the desired collection_name explicitly to build_knowledge_base().
collection_name = "my_new_collection"
kb, chromaDB_status = kb_loader.build_knowledge_base(
    collection_name,
    document_directory_path=r'.\tests\sample_documents',
    add_documents=True
)

# 2) Open an existing collection by name (fails if DB or collection missing).
#    Use load_knowledge_base for open-only semantics.
# collection_name = "my_new_collection"
# kb, chromaDB_status = kb_loader.load_knowledge_base(collection_name)


print("--------------------- CHROMADB STATUS ---------------------\n", getattr(chromaDB_status, "value", str(chromaDB_status)))

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


