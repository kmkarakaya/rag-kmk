# rag-kmk

[![image](https://img.shields.io/pypi/v/rag-kmk.svg)](https://pypi.python.org/pypi/rag-kmk)
[![image](https://img.shields.io/conda/vn/conda-forge/rag-kmk.svg)](https://anaconda.org/conda-forge/rag-kmk)

A compact helper library for small Retrieval-Augmented Generation (RAG) workflows.

- Free software: MIT License
- Docs: see `docs/` for examples and developer notes

## Quick install

pip:
```powershell
pip install rag-kmk
```

From source:
```powershell
git clone https://github.com/kmkarakaya/rag-kmk.git
cd rag-kmk
pip install -e .
```

## Quick start — minimal examples

Keep examples short (<= 20 lines). Use environment variables for API keys.

1) Load configuration explicitly (recommended):
```python
from rag_kmk import initialize_rag, CONFIG

# load default config file and get the config dict
cfg = initialize_rag()
# or use the module-level CONFIG (may be empty if loading failed at import time)
print(CONFIG.get('llm'))
```

2) Create a persistent collection and ingest documents:
```python
from rag_kmk.knowledge_base import build_knowledge_base

kb, status = build_knowledge_base(
  collection_name='my_collection',
  document_directory_path=r'tests\sample_documents',
  add_documents=True,
)
print(status)
```

3) Open an existing persistent collection (open-only semantics):
```python
from rag_kmk.knowledge_base import load_knowledge_base

kb, status = load_knowledge_base('my_collection')
print(status)
```

4) Create an ephemeral (directory-backed) collection for tests (use a temporary directory):
```python
from rag_kmk.knowledge_base import build_knowledge_base
import tempfile

with tempfile.TemporaryDirectory() as td:
    kb, status = build_knowledge_base(
      collection_name='tmp',
      document_directory_path=r'tests\sample_documents',
      add_documents=True,
      chromaDB_path=td,  # use a temporary filesystem directory for this run (ephemeral)
    )
    print(status)
# data removed when the temp dir is deleted
```

5) Build a ChatClient and run the simple pipeline (see `run.py` for a canonical example):
```python
from rag_kmk.chat_flow.llm_interface import build_chatBot, run_rag_pipeline

client = build_chatBot(CONFIG.get('llm', {}))
try:
    run_rag_pipeline(client, kb, non_interactive=True)
finally:
    client.close()
```

## Configuration

Important config keys (see `rag_kmk/config/config.yaml`):
- llm:
  - api_key — direct API key (not recommended in source)
  - api_key_env_var — name of environment variable that holds the API key
  - model — model identifier used by the configured LLM backend
  - system_prompt — optional system instruction
- vector_db:
  - chromaDB_path — filesystem path for persistent ChromaDB; set to a directory path for persistent storage

Notes:
- Legacy key `chroma_db` is accepted and normalized to `chromaDB_path` by `load_config()`.
- Use `rag_kmk.config.config.mask_config(cfg)` when printing or logging config to avoid leaking secrets.
- Prefer calling `initialize_rag()` or `load_config()` explicitly in long-running programs instead of relying on the import-time `CONFIG` population.

## API reference (short)
Primary helpers and their key parameters (one-line):

- rag_kmk.initialize_rag(custom_config_path=None) -> dict
  - Loads config using `load_config()` and returns the config dict.
- rag_kmk.config.config.load_config(config_path=None) -> dict
  - Loads and normalizes repository config (populates module CONFIG).
- rag_kmk.config.config.mask_config(config, keys=('api_key','api_key_env_var')) -> dict
  - Returns a shallow copy with sensitive values masked for safe logging.
- rag_kmk.knowledge_base.document_loader.build_knowledge_base(collection_name: str,
      document_directory_path: Optional[str]=None, add_documents: bool=False,
      chromaDB_path: Optional[str]=None, cfg: Optional[dict]=None, overwrite: bool=False)
  -> (collection, ChromaDBStatus)
  - Create (or open) a collection and optionally ingest documents.
- rag_kmk.knowledge_base.document_loader.load_knowledge_base(collection_name: str, cfg: Optional[dict]=None)
  -> (collection or None, ChromaDBStatus)
  - Open-only helper (does not create directories).
- rag_kmk.vector_db.database.create_chroma_client(collection_name='default', chromaDB_path=None, create_new=True, config=None)
  -> (client, collection, ChromaDBStatus)
- rag_kmk.vector_db.database.ChromaDBStatus
  - Enum-like statuses (OK, NEW_PERSISTENT_CREATED, MISSING_PERSISTENT, ALREADY_EXISTS, ERROR, ...)
- rag_kmk.vector_db.database.summarize_collection(chroma_collection)
  - Best-effort print + return of a JSON summary for a collection.
- rag_kmk.chat_flow.llm_interface.build_chatBot(config: Optional[dict]=None) -> ChatClient
  - Lazily builds an LLM-backed ChatClient or returns a no-op client when SDK/creds missing.
- rag_kmk.chat_flow.llm_interface.generate_LLM_answer(client, prompt: str, timeout_seconds: int=30, **opts) -> str
  - Runs client generation with a timeout and returns text output.
- rag_kmk.chat_flow.llm_interface.run_rag_pipeline(client, kb_collection, non_interactive: bool=False)
  - Small interactive loop (prints to stdout); supply non_interactive=True in scripts/CI.
- rag_kmk.utils.compute_fingerprint(path: str) -> str
  - SHA256 hex digest for a file; raises FileNotFoundError if missing.
- rag_kmk.utils.now_isoutc() -> str
  - Current UTC timestamp as ISO8601 string ending with 'Z'.

If you need exact parameter details, consult the module source in `rag_kmk/` (this README aims to be a concise reference).

## Persistence & semantics

Path resolution precedence used by `build_knowledge_base()`:
1. explicit `chromaDB_path` argument
2. `cfg.get('vector_db', {}).get('chromaDB_path')` returned by `load_config()`
3. default: `./chromaDB` created under the current working directory

- Notes on persistence behavior (persistent-only):
- The library requires a filesystem path for persistent ChromaDB. Pass a directory to `chromaDB_path` or configure `vector_db.chromaDB_path` in the config.
- Supplying a filesystem path forces persistent storage; `build_knowledge_base` will create the path if needed.
- There is no `force_persistence` boolean parameter in the current API; control persistence explicitly via `chromaDB_path` or by using `create_chroma_client(..., create_new=True/False)`.

## Development & testing

- Run tests:
```powershell
pytest -q tests
```
- Coverage helper (repository includes a helper script):
```powershell
scripts\run_coverage.bat
```
- An environment spec exists at `env-rag-backup.yml`.

## Contributing & CI

- See `docs/contributing.md` for contribution guidelines.
- CI workflows are under `.github/workflows/`.

## Troubleshooting & notes

- If the LLM SDK or credentials are missing the library returns a no-op ChatClient so non-LLM parts of the pipeline continue to work.
- `generate_LLM_answer()` enforces a timeout (default 30s) and raises a RuntimeError on timeout.
- When debugging auth or model issues, print `rag_kmk.config.config.mask_config(config)` rather than the raw config to avoid leaking secrets.

## What's new (changelog fragment)

- README updated to reflect actual current APIs: use `initialize_rag()` / `build_knowledge_base()` signatures from source.
- Clarified persistence resolution (explicit arg > config > default) and removed references to a non-existent `force_persistence` parameter.

---
For more examples and developer notes see `docs/` and `run.py` (canonical usage example).

