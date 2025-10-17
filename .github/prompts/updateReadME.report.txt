Sorted files scanned under rag_kmk/ (alphabetical):

rag_kmk/__init__.py
rag_kmk/chat_flow/__init__.py
rag_kmk/chat_flow/llm_interface.py
rag_kmk/config/config.py
rag_kmk/config/config.yaml
rag_kmk/knowledge_base/__init__.py
rag_kmk/knowledge_base/document_loader.py
rag_kmk/knowledge_base/text_splitter.py
rag_kmk/vector_db/__init__.py
rag_kmk/vector_db/database.py
rag_kmk/vector_db/query.py
rag_kmk/utils.py
rag_kmk/exceptions.py
rag_kmk/knowledge_base.py

Per-file discoveries (one-line per exported item) and notes:

- rag_kmk/__init__.py
  - Exports: initialize_rag(custom_config_path=None) -> dict, CONFIG (dict), load_config, mask_config
  - Notes: populates CONFIG at import time inside try/except; instructs callers to use initialize_rag() for explicit loading.
  - README impact: keep mention of initialize_rag() and CONFIG; no change needed beyond examples.

- rag_kmk/chat_flow/__init__.py
  - Exports: build_chatBot, generate_LLM_answer, generateAnswer, run_rag_pipeline, RAG_LLM
  - Notes: re-exports llm_interface functions; RAG_LLM is a backwards-compatible None placeholder.
  - README impact: ensure import paths used in examples are from rag_kmk.chat_flow.llm_interface or package root.

- rag_kmk/chat_flow/llm_interface.py
  - Public classes/functions:
    - class ChatClient: supports_streaming (bool), generate(prompt: str, **opts) -> str, close() -> None
    - build_chatBot(config: Optional[Dict[str, Any]] = None) -> ChatClient
    - generate_LLM_answer(client: ChatClient, prompt: str, timeout_seconds: int = 30, **opts) -> str
    - run_rag_pipeline(client: ChatClient, kb_collection: Any, non_interactive: bool = False) -> None
    - generateAnswer(client: Any, chroma_collection: Any = None, query: str = '', n_results: int = 5, only_response: bool = False) -> str
  - Notes: build_chatBot lazily imports google.genai and returns a NoOp client if api_key/model missing; generate_LLM_answer enforces timeout using ThreadPoolExecutor.
  - To-do/Questions: None (signatures are static).
  - README impact: Document ChatClient behavior and timeout semantics; show example using build_chatBot and run_rag_pipeline.

- rag_kmk/config/config.py
  - Public functions:
    - _normalize_vector_db_config(cfg: dict) -> dict (internal but useful for docs)
    - load_config(config_path: str = None) -> dict
    - mask_config(config: dict, keys: tuple = ('api_key', 'api_key_env_var')) -> dict
  - Exports: CONFIG module variable (populated when load_config called)
  - Notes: load_config normalizes legacy 'chroma_db' -> 'chromaDB_path' and replaces path fragments 'chroma_db' with 'chromaDB'.
  - README impact: Include config keys from config.yaml and mention normalization behavior.

- rag_kmk/config/config.yaml
  - Keys discovered (top-level): vector_db, llm, knowledge_base, rag, api_keys, logging, supported_file_types
  - Important subkeys:
    - vector_db: type, chromaDB_path, collection_name, embedding_model, tokens_per_chunk, category
    - llm: type, model, settings.system_prompt, settings.temperature
    - knowledge_base: chunk_size, chunk_overlap, max_file_size
    - rag: num_chunks_to_retrieve, similarity_threshold
    - api_keys.google_ai
  - README impact: Include minimal Configuration section listing these keys and explain precedence for chromaDB_path.

- rag_kmk/knowledge_base/__init__.py
  - Re-exports: build_knowledge_base, load_and_add_documents
  - README impact: Ensure examples import build_knowledge_base and load_knowledge_base from rag_kmk.knowledge_base.

- rag_kmk/knowledge_base/document_loader.py
  - Public functions and signatures:
    - load_and_add_documents(chroma_collection, document_directory_path, cfg) -> (files_processed: bool, errors: list[str])
    - load_knowledge_base(collection_name: str, cfg: Optional[dict] = None) -> Tuple[Optional[object], vdb_database.ChromaDBStatus]
    - build_knowledge_base(collection_name: str, document_directory_path: Optional[str] = None, add_documents: bool = False, chromaDB_path: Optional[str] = None, cfg: Optional[dict] = None, overwrite: bool = False) -> Tuple[Optional[object], vdb_database.ChromaDBStatus]
  - Notes: build_knowledge_base resolves chromaDB_path with precedence: explicit arg > cfg['vector_db']['chromaDB_path'] > default ./chromaDB; creates directory when needed; returns status from vector_db.database.ChromaDBStatus.
  - To-do/Questions: None.
  - README impact: Provide exact signatures in API Reference and show minimal ingestion example.

- rag_kmk/knowledge_base/text_splitter.py
  - Public functions:
    - convert_Pages_ChunkinChar(text_in_pages, chunk_size=None, chunk_overlap=None)
    - convert_Chunk_Token(text_chunksinChar, sentence_transformer_model=None, chunk_overlap=None, tokens_per_chunk=None)
    - add_document_to_collection(ids, metadatas, text_chunksinTokens, chroma_collection)
    - add_meta_data(text_chunksinTokens, title, initial_id, category=None) -> (ids, metadatas)
  - Notes: Uses `rag_kmk.CONFIG` lazily for defaults; relies on langchain text splitters and sentence-transformers.
  - README impact: Add one-line descriptions for these helpers in API reference and mention dependency on langchain/sentence-transformers for splitting.

- rag_kmk/vector_db/__init__.py
  - Re-exports: create_chroma_client, summarize_collection, retrieve_chunks, show_results
  - README impact: Document create_chroma_client and summarize_collection signatures.

- rag_kmk/vector_db/database.py
  - Public:
    - class ChromaDBStatus(Enum)
    - create_chroma_client(collection_name: str = 'default', chromaDB_path: str = None, create_new: bool = True, config: dict = None) -> (client, collection, status)
    - get_client_for_collection(collection)
    - summarize_collection(chroma_collection) -> str (JSON)
    - list_collection_names(client) -> List[str]
  - Notes: robust compatibility for multiple chromadb versions; many fallback paths.
  - README impact: Add one-line descriptions and usage notes for persistence vs in-memory.
  - Note: This code previously exposed an "in-memory" creation path when `chromaDB_path` was None. That behavior has been removed — callers must provide a persistent `chromaDB_path` (or rely on the config/default path). Tests and README were updated accordingly.

- rag_kmk/vector_db/query.py
  - Public functions:
    - retrieve_chunks(chroma_collection, query, n_results=5, return_only_docs=False, filterType=None, filterValue=None)
    - show_results(results, return_only_docs=False)
  - Notes: Expects chroma_collection.query API shape; returns dict with 'documents','metadatas','distances' or list when return_only_docs=True.
  - README impact: Add retrieval example showing retrieve_chunks(..., return_only_docs=True).

- rag_kmk/utils.py
  - Public functions:
    - compute_fingerprint(path: str) -> str
    - now_isoutc() -> str
  - README impact: Keep small utility descriptions.

- rag_kmk/exceptions.py
  - Public exception classes: MissingAPIKey, LLMInitError, IndexingError, GenerationError
  - README impact: Mention common exceptions in Troubleshooting section.

- rag_kmk/knowledge_base.py
  - Re-exports: build_knowledge_base, load_and_add_documents
  - README impact: examples should import from rag_kmk.knowledge_base as used above.

Mismatches found vs existing README.md
- Some examples in README used `from rag_kmk.knowledge_base import document_loader as kb_loader` and then called functions; the library exposes `build_knowledge_base` at package-level so examples were updated to import directly.
- README already correctly documents most function signatures; minor cleanup performed to align imports.

To-do / Questions (items that require human input or runtime info):
- Confirm preferred example import style: README now uses `from rag_kmk.knowledge_base import build_knowledge_base` which is concise and reflects `__all__` exports. If the project prefers `from rag_kmk.knowledge_base import document_loader`, adjust accordingly.
- No runtime-only dynamic signatures discovered; static analysis sufficed.

Validation summary:
- All required files under `rag_kmk/` were read and APIs extracted.
- Config keys from `rag_kmk/config/config.yaml` were included in discoveries.

End of report.
