# Copilot repository instructions (compact)

This file contains compact, contributor-facing instructions to help Copilot-style agents and humans work on the project consistently.

## Overview

**rag-kmk** is a small educational Retrieval-Augmented Generation (RAG) Python project demonstrating document ingestion, vector indexing (Chroma), and a simple chat/query flow. It's packaged as a Python library under `rag_kmk/` and can be installed with `pip install rag-kmk`.

Quick signals
- Language: Python (>=3.9 from `pyproject.toml`)
- Main code: `rag_kmk/` (document loader, text splitter, vector DB wrapper, chat flow)
- Runners/examples: `run.py`, `run_interface.py`, `run_interface2.py`
- Tests: `tests/` (pytest)
- Docs: `docs/`
- Local DB: `./chromaDB/` (persistent by default)

IMPORTANT: `run.py` is an example entrypoint and MUST NOT be changed to add features or fix bugs. All feature or bug-fix work should be implemented inside the library code under `rag_kmk/`. The runner exists only as an example and distribution entry point.

## What to do (developer guidance)

- Prefer small, idiomatic Python changes. Keep compatibility with Python 3.8+.
- When adding features: include one happy-path unit test plus one edge-case test using pytest.
- Add concise docstrings for new public functions and update `docs/` or `README.md` with a short usage snippet when helpful.
- Test guidance: tests under `tests/` should exercise the library modules inside `rag_kmk/` (import `rag_kmk.*`). Tests must avoid executing example runner scripts (like `run.py`) directly — instead call the library functions or monkeypatch `rag_kmk` submodules for isolation.
 - Configuration: all code and tests must use the config files located in `rag_kmk/config/` and access them via the library's config loader (`rag_kmk.config` or the helper functions provided). Do not hardcode configuration values in tests — prefer loading `config/config.yaml` or using monkeypatched loader helpers.
 - Testing policy: tests must validate the actual `rag_kmk` library implementations (call library functions and assert their behavior). Tests are allowed to mock or stub third-party SDKs (for example `chromadb` or an LLM SDK) to avoid external network or system dependencies, but must not replace or monkeypatch internal `rag_kmk` functions or modules as a shortcut. When the behavior depends on external systems, prefer separate integration tests that run with real third-party services (documented in this file).

## What to avoid

- Never add secrets or credentials; use environment variables or placeholders (e.g. `os.environ.get("OPENAI_API_KEY")`).
- Avoid large multi-file rewrites in a single PR. Keep changes focused and reviewable.
- Don't modify `run.py` to fix library bugs or add features.

## Conda development environment (recommended)

Reproducible local development uses a `conda` environment named `rag`. Use these PowerShell-friendly steps:

1) Create and activate the environment

```powershell
conda create -n rag python=3.12 -y
conda activate rag
```

2) Install dependencies

```powershell
# prefer pip install from the pinned requirements file
pip install -r requirements.txt

# install pytest for running tests
pip install pytest
```

3) Verify the environment and run tests

```powershell
python -c "import sys, os; print('PYTHON:', sys.executable); print('CONDA_ENV:', os.environ.get('CONDA_DEFAULT_ENV'))"
python -m pytest -q
```

Notes
- If you need GPU-enabled packages (e.g. sentence-transformers with CUDA), prefer vendor instructions and `conda` packages for compatibility.
- Use environment variables for API keys and do not commit secrets.

## Examples Copilot can produce

- Tiny unit test template for a function in `rag_kmk/` (fast, isolated, mocks external calls).
- Small helper (text normalization) with docstring and tests.
- README snippet that demonstrates loading `tests/sample_documents/` and running a query.

## Helpful file signals for context

- `pyproject.toml`, `requirements.txt`, `tests/conftest.py`, `tests/`, `rag_kmk/`, `docs/`

## Security note

- Do not include API keys or private data in suggestions. Use placeholders and call out env vars.
