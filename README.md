# rag-kmk


[![image](https://img.shields.io/pypi/v/rag-kmk.svg)](https://pypi.python.org/pypi/rag-kmk)
[![image](https://img.shields.io/conda/vn/conda-forge/rag-kmk.svg)](https://anaconda.org/conda-forge/rag-kmk)


**A simple RAG implementation for educational purposes implemented by Murat Karakaya Akademi**


-   Free software: MIT License
-   Documentation: https://kmkarakaya.github.io/rag-kmk
-   Tutorial: https://www.youtube.com/@MuratKarakayaAkademi
    

## Features

- TODO: 
- add other file types

## Local development notes

- The project stores a local persistent ChromaDB under `./chromaDB` by default.
- To avoid checking runtime DB files into source control, add `chromaDB/` to your `.gitignore`.

If you need to switch to an in-memory collection for quick tests, set `vector_db.chromaDB_path` to `null` in `rag_kmk/config/config.yaml`.

## What's new (important)

- The `build_knowledge_base()` helper in `rag_kmk.knowledge_base.document_loader` now accepts a
	`force_persistence: Optional[bool]` parameter to disambiguate whether the caller requires a
	persistent ChromaDB on disk or prefers an in-memory collection. This makes the behavior explicit
	across four common use-cases:

	1. Load an existing persistent collection and add documents to it.
	2. Load an existing persistent collection without adding documents.
	3. Create a new in-memory collection and add documents to it.
	4. Create a new persistent collection on disk and add documents to it.

### Parameter precedence and semantics

- Resolution order for the ChromaDB path (what decides persistent vs in-memory):
	1. The explicit `chromaDB_path` argument passed to `build_knowledge_base()` (including an
		 explicit `None` to force in-memory).
	2. The project configuration loaded via `rag_kmk.config.config.load_config()` (this preserves
		 test monkeypatch behavior; prefer passing an explicit `config` to override in tests).
	3. If none of the above provide a path, the function will choose in-memory when adding
		 documents by default unless `force_persistence=True` is passed.

- `force_persistence` values:
	- True: require a persistent (on-disk) collection. A ValueError is raised if no persistent
		path can be resolved.
	- False: force creation/use of an in-memory collection.
	- None: the function follows the resolution rules above and only requires persistence when a
		persistent path is present (or when `create_new` is True and a persistent path is explicitly
		provided).

### Examples

Assume you imported the helper:

```python
from rag_kmk.knowledge_base.document_loader import build_knowledge_base
from rag_kmk.config.config import load_config

# 1) Load persistent DB (from config or explicit path) and add documents
cfg = load_config()
build_knowledge_base(document_directory_path='tests/sample_documents/', add_documents=True, config=cfg)

# 2) Load persistent DB but do not add documents
build_knowledge_base(document_directory_path=None, add_documents=False, config=cfg)

# 3) Create an in-memory collection and add documents (explicitly force in-memory)
build_knowledge_base(document_directory_path='tests/sample_documents/', chromaDB_path=None, add_documents=True)

# 4) Create a persistent collection and add documents (force persistence requirement)
build_knowledge_base(document_directory_path='tests/sample_documents/', force_persistence=True, chromaDB_path='./chromaDB')
```

Notes:
- If you pass `document_directory_path=None` ingestion will be skipped and the function will only
	open or create the collection as needed.
- The function accepts both the older and newer return/value shapes from the ChromaDB factory
	under the hood; callers should not rely on implementation details of the DB factory.

## Testing and development environment

- A Conda environment spec is available at `env-rag-backup.yml`. To create and activate it:

```powershell
conda env create -f env-rag-backup.yml; conda activate rag
```

- Run the test suite with pytest:

```powershell
pytest -q tests
```

- The repository includes `pytest.ini` which filters noisy SWIG-related DeprecationWarnings that
	can appear during test runs. If you change or remove that file you may see those warnings again.

## Continuous integration

- A GitHub Actions workflow has been added at `.github/workflows/ci.yml` which runs the test suite
	on push and pull requests. The workflow relies on the same `pytest.ini` to keep CI logs concise.

## Notes and troubleshooting

- By default the project will persist a local ChromaDB under `./chromaDB`. If you need purely
	ephemeral behavior for quick experiments, pass `chromaDB_path=None` or `force_persistence=False`.
- Do not commit the `chromaDB/` folder; it's intended to be ignored in source control.

