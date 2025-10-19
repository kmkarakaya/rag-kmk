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
import json

# Ensure CONFIG is populated (some workflows populate CONFIG lazily)
if not isinstance(CONFIG, dict):
	import rag_kmk as _rag_mod
	try:
		from rag_kmk.config import config as _cfg_mod
		_loaded = _cfg_mod.load_config(None)
		# update package-level CONFIG and local binding
		_rag_mod.CONFIG = _loaded
		CONFIG = _rag_mod.CONFIG
	except Exception:
		# best-effort fallback: ensure CONFIG is at least an empty dict to avoid TypeError
		_rag_mod.CONFIG = {}
		CONFIG = _rag_mod.CONFIG

# Import rag_client only after CONFIG is ready
from rag_kmk import rag_client

print("--------------------- ORIGINAL CONFIG ---------------------\n", CONFIG.get('llm'))
# Only update the LLM model; all other config values remain as in config.yaml
CONFIG['llm']['model'] = 'gemini-2.5-flash'
print("--------------------- AFTER CONFIG UPDATE ---------------------\n", CONFIG['llm'])
print("-----------------"*4)

rag = rag_client()

# 1) List all collections
print("📦 Collections in ChromaDB:", json.dumps(rag.list_collections(), indent=2))

collection_name = "my_new_collectionX"
# 7) Delete the collection
print(f"🗑️ Delete collection '{collection_name}' result:", json.dumps(
    rag.delete_collection(collection_name), indent=2))

# 2) Create a new collection

print(f"ℹ️ Create collection '{collection_name}' result:", json.dumps(
    rag.create_collection(collection_name), indent=2))

# 3) Add documents to collection (uncomment and adjust doc_path as needed)
# doc_path = "tests/sample_documents"
# print(f"➕ Add documents to '{collection_name}':", json.dumps(
#     rag.add_doc(collection_name, doc_path=doc_path), indent=2))

# 4) Load the collection
print(f"ℹ️ Load collection '{collection_name}' result:", json.dumps(
    rag.load_collection(collection_name), indent=2))

# 5) Summarize the collection
print("--------------------- COLLECTION SUMMARY BEFORE ADDING DOCUMENTS ---------------------\n")
print(json.dumps(rag.summarize_collection(collection_name), indent=2))

# 6) Add documents to collection (uncomment and adjust doc_path as needed)
doc_path = "tests/sample_documents"
rag.add_doc(collection_name, doc_path=doc_path)
print("--------------------- COLLECTION SUMMARY AFTER ADDING DOCUMENTS ---------------------\n")
print(json.dumps(rag.summarize_collection(collection_name), indent=2))


# 6) Chat with the collection (uncomment to use)
prompt = "KDV hakkında verilen cevap nedir?"
print(f"💬 Chat result:", json.dumps(
    rag.chat(collection_name, prompt=prompt), indent=2))

prompt = "bu sohbetin başında sana ne sordum?"
print(f"💬 Chat result:", json.dumps(
    rag.chat(collection_name, prompt=prompt), indent=2))



# 8) Build knowledge base (uncomment and adjust as needed)
# print("🏗️ Build knowledge base:", json.dumps(
#     rag.build_knowledge_base(collection_name, document_directory_path=doc_path, add_documents=True), indent=2))

# 9) Load knowledge base (uncomment and adjust as needed)
# print("📚 Load knowledge base:", json.dumps(
#     rag.load_knowledge_base(collection_name), indent=2))

# 10) Mask config for safe logging
# print("🔒 Masked config:", json.dumps(rag.mask_config(), indent=2))

# 11) Reload config (demonstrate config reload)
# print("🔄 Reload config:", json.dumps(rag.reload_config(), indent=2))

# 12) Generate LLM answer directly (uncomment to use)
# print("🤖 LLM answer:", json.dumps(
#     rag.generate_llm_answer("Summarize the collection."), indent=2))

# 13) Run RAG pipeline (uncomment to use)
# print("🚀 Run RAG pipeline:", json.dumps(
#     rag.run_rag_pipeline(collection_name, non_interactive=True), indent=2))

# Clean up
rag.close()
print("-----------------"*4)


