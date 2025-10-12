# Copilot repository instructions (compact)

**rag-kmk** is a small educational Retrieval-Augmented Generation (RAG) Python project that demonstrates document ingestion, vector indexing (Chroma), and simple query/chat flow. It is packaged as a Python library and can be installed via `pip install rag-kmk`.

Quick repo facts (signals)

- Language: Python (>=3.8 from `pyproject.toml`)
- Key libs (see `requirements.txt`): numpy, PyYAML, PyMuPDF, python-docx, langchain, sentence-transformers, google-genai, chromadb, streamlit, docx2txt
- Main code: `rag_kmk/` (document loader, text splitter, vector DB wrapper, chat flow)
- Runners: `run.py`, `run_interface.py`, `run_interface2.py`
- Tests: `tests/` (pytest)
- Docs: `docs/`
- Local DB: `./chroma_db/` (persistent by default)

What to do (short)

- Prefer small, idiomatic Python changes. Keep compatibility with Python 3.8+.
- When adding features: include one happy-path unit test + one edge-case test using pytest.
- Add concise docstrings and update `docs/` or `README.md` with short usage snippets.

What to avoid (short)

- Never add secrets or credentials; use env var placeholders (e.g. `os.environ.get("OPENAI_API_KEY")`).
- Avoid large multi-file rewrites in a single change. No license-violating or proprietary code.

Examples Copilot can produce

- Tiny unit test template for a function in `rag_kmk/` (fast, isolated, mocks external calls).
- Small helper (text normalization) + docstring + tests.
- README snippet that demonstrates loading `tests/sample_documents/` and running a query.

Helpful file signals for context

- `pyproject.toml`, `requirements.txt`, `tests/conftest.py`, `tests/`, `rag_kmk/`, `docs/`

Security note

- Do not include API keys or private data in suggestions. Use placeholders and call out env vars.
