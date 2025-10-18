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
from rag_kmk.vector_db.database import (
    create_chromadb_client,
    create_collection,
    load_collection,
    list_collection_names,
    summarize_collection,
    ChromaDBStatus,
    get_client_for_collection,
)

import json

print("--------------------- ORIGINAL CONFIG ---------------------\n", CONFIG['llm'])
# Only update the LLM model; all other config values remain as in config.yaml
CONFIG['llm']['model'] = 'gemini-2.5-flash'
print("--------------------- AFTER CONFIG UPDATE ---------------------\n", CONFIG['llm'])
print("-----------------"*4)
# Set your persistent ChromaDB path
#chromaDB_path = 'path/to/chromadb'  # replace with your actual path

# 1) Create/load persistent ChromaDB client
client_result = create_chromadb_client()
print("📢 ChromaDB client status:", client_result['status'])
if client_result['client'] is None:
    print("🚩 Failed to create/load ChromaDB client.", client_result.get('error'))
    exit(1)
client = client_result['client']

# 2) List all collections in the persistent ChromaDB
collections_result = list_collection_names(client)
print("📦Collections in ChromaDB:", json.dumps(collections_result, indent=2))

# 3) Try to create a new collection
collection_name = "my_new_collection"
create_result, created_collection = create_collection(client, collection_name)
print(f"ℹ️ Create collection '{collection_name}' result:", json.dumps(
    create_result, indent=2))

if created_collection is not None:
    print(f"👍Created collection: {collection_name}")
else:
    print(f"🚩Collection '{collection_name}' already exists or error. {create_result.get('error')}")

# 4) Try to load the collection (should succeed if just created or already exists)
collection_load_result, loaded_collection = load_collection(client, collection_name)
if loaded_collection is not None:
    print(f"👍Loaded collection: {collection_name}")
    print("--------------------- CHROMADB SUMMARY ---------------------\n")
    summary_result = summarize_collection(loaded_collection)
    print(json.dumps(summary_result, indent=2))
else:
    print(collection_load_result['error'])

# 5) Try to load a non-existent collection
nonexist_result, nonexist_collection = load_collection(client, "does_not_exist")
print("ℹ️ Load non-existent collection result:", json.dumps(
    nonexist_result, indent=2))
if nonexist_collection is None:
    print("👍Correctly handled missing collection.")

# 6) List collections again to verify
collections_result = list_collection_names(client)
print("Collections in ChromaDB after operations:", json.dumps(collections_result, indent=2))

# 7) (Optional) Run RAG pipeline if collection loaded
if loaded_collection is not None:
    print("--------------------- RUN RAG PIPELINE ---------------------\n")
    chat_client = chat_flow.build_chatBot(CONFIG.get('llm', {}))
    try:
        chat_flow.run_rag_pipeline(chat_client, loaded_collection)
    finally:
        try:
            chat_client.close()
        except Exception:
            pass
else:
    print("🚩No valid collection loaded for RAG pipeline.")

print("-----------------"*4)
# Example: Try to create a client with an invalid path
invalid_client_result = create_chromadb_client("invalid/path/<>")
print("❌ Example invalid client creation:", json.dumps(
    {k: v for k, v in invalid_client_result.items() if k != 'client'}, indent=2))

# Example: Use get_client_for_collection
if loaded_collection is not None:
    found_client = get_client_for_collection(loaded_collection)
    print("🔎 get_client_for_collection result:",
          "Found client" if found_client is not None else "No client found")

# Example: Use summarize_collection directly with error handling
summary_result = summarize_collection(loaded_collection)
if summary_result['status'] == 'OK':
    print("📊 Collection summary (direct):", json.dumps(summary_result, indent=2))
else:
    print("⚠️ Could not summarize collection:", summary_result['error'])

# end of minimal run.py


