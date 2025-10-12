
Improve RAG-KMK: actionable development prompt for a coding agent
===============================================================

Overview
--------
You are a coding agent assigned to improve the `rag_kmk` Python library. This repository implements a RAG (retrieval-augmented generation) pipeline but currently mixes library initialization with CLI side-effects, lacks deduplication/provenance, and has limited test coverage. Your job is to implement a sequence of safe, test-covered changes that make `rag_kmk` usable as a programmatic library and robust CLI.

Goals (primary)
- Remove import-time side effects and make the library safe to import.
- Provide a clear, testable CLI (`run.py`) that uses the library API and accepts flags for `--docs`, `--chroma-path`, `--index-only`, `--model`, `--smoke`, and `--debug`.
- Add a minimal fingerprint/deduplication strategy and standard metadata keys for ingested documents.
- Replace prints with structured logging and add tests for the main flows.

Constraints
- Make small, incremental changes. Do not rewrite the entire codebase in one change.
- Preserve existing public function names unless making a clear API improvement with compatibility helpers.
- Tests must run quickly and not require network access to real LLMs; stub or mock LLM clients and chroma collections.

Phases (ordered)
-----------------
Phase 1 — Safety & import hygiene (high priority)
- Remove any code that constructs network clients or reads config files at module import time. Focus files: `rag_kmk/__init__.py` and `rag_kmk/chat_flow/__init__.py`.
- Replace module-level instantiation like `RAG_LLM = build_chatBot()` with an exported builder function `build_chatBot(config)`.
- Add a small `exceptions.py` with exception classes: `MissingAPIKey`, `LLMInitError`, `IndexingError`, `GenerationError`.
 - Ensure `rag_kmk/__init__.py` does NOT call `initialize_rag('./config.yaml')` at import time; instead export `initialize_rag()` for callers to run explicitly.

API contract (one-line signatures) — add this to the prompt so the agent implements predictable functions
- `rag_kmk/chat_flow.py` or `rag_kmk/chat_flow/__init__.py` should export:
	- `def build_chatBot(config: dict) -> ChatClient`  # ChatClient minimal interface below
	- `def generate_LLM_answer(client: ChatClient, prompt: str, **opts) -> str`
	- `def run_rag_pipeline(client: ChatClient, kb: KnowledgeBase, non_interactive: bool=False) -> None`

- `rag_kmk/knowledge_base.py` should export:
	- `def build_knowledge_base(document_directory_path: Optional[str]=None, chromaDB_path: Optional[str]=None, persist: bool=False, metadata_strategy: Optional[callable]=None) -> Tuple[KnowledgeBase, Status]`

- Minimal ChatClient interface (document in prompt):
	- `class ChatClient: generate(prompt: str, **opts) -> str; close() -> None; supports_streaming: bool`

File locations (required)
- `rag_kmk/exceptions.py` — add exception classes.
- `rag_kmk/config.py` — add `load_config(path=None) -> dict` and `mask_config(config, keys=tuple)`.
- `rag_kmk/utils.py` — add `compute_fingerprint(path: str) -> str` and small helpers.


Acceptance criteria (Phase 1)
- Importing `rag_kmk` does not perform network calls or read environment files. Validate with a unit test that imports the package while mocking network-related functions and asserting they are not called.
- `rag_kmk.chat_flow` exports `build_chatBot` but does not create a `RAG_LLM` instance at import time.

Phase 2 — CLI refactor and `run.py` hygiene (high priority)
- Refactor `run.py` to:
	- Use `argparse` with flags: `--docs`, `--chroma-path`, `--index-only`, `--model`, `--smoke`, `--debug`.
	- Avoid mutating `rag_kmk.CONFIG` in-place; copy it with `deepcopy` and apply CLI overrides.
	- Build the LLM client locally using `build_chatBot(local_config['llm'])` inside `main()` and handle exceptions.
	- Replace `print()` calls with `logging` (respect `--debug`).
	- Ensure `main(argv=None)` returns an integer exit code and `if __name__ == '__main__': sys.exit(main())` is used.

Acceptance criteria (Phase 2)
- `run.py --smoke` runs without prompting and exits code 0 using the sample documents (or mocked KB). Provide tests that patch `build_knowledge_base` and `build_chatBot` and assert `main(['--smoke'])` returns 0.
- `run.py --index-only --docs tests/sample_documents` calls `build_knowledge_base` with the provided path and exits after summarizing.

Exit codes (standardize for CLI)
- `0` — success
- `1` — usage / invalid args
- `2` — initialization failure (e.g., missing API key or failed build_chatBot)
- `3` — indexing error (IndexingError)
- `4` — generation error (GenerationError)


Phase 3 — Metadata & deduplication (high priority)
- Add `compute_fingerprint(path)` (sha256 hex) in `rag_kmk/knowledge_base` or `rag_kmk/utils.py`.
- Ensure `build_knowledge_base` computes fingerprint per document and includes metadata keys: `source_path`, `created_at` (ISO8601 UTC), `fingerprint`, `document`, and `category` (if available).
- When `persist=True` or `chromaDB_path` is provided, check existing collection metadata for matching fingerprints and skip indexing duplicates.

Acceptance criteria (Phase 3)
- Unit test: ingest a small sample file, then attempt to ingest the same file again with persistent DB; assert the second indexing run does not increase vector count.
- Unit test: metadata returned for chunks contains `fingerprint`, `source_path` and `created_at`.

Test skeletons (pytest) — provide these snippets to the coding agent so tests are straightforward to implement

1) `tests/test_llm_interface_retry.py`
```py
def test_llm_retry(monkeypatch):
	from rag_kmk.chat_flow import generate_LLM_answer, build_chatBot

	class FakeClient:
		def __init__(self):
			self.calls = 0
		def generate(self, prompt, **opts):
			self.calls += 1
			if self.calls == 1:
				raise RuntimeError('client has been closed')
			return 'ok'
		def close(self):
			pass

	client = FakeClient()
	out = generate_LLM_answer(client, 'hello')
	assert out == 'ok'
	assert client.calls == 2
```

2) `tests/test_document_loader_branches.py` (skeleton)
```py
def test_document_loader_fingerprint(tmp_path):
	# write a small txt file
	p = tmp_path / 'a.txt'
	p.write_text('hello world')
	from rag_kmk.knowledge_base import build_knowledge_base, compute_fingerprint
	fp = compute_fingerprint(str(p))
	kb, status = build_knowledge_base(document_directory_path=str(tmp_path))
	# assert metadata present on first chunk
	first = kb.get_first_chunk()  # implement a test helper on fake KB
	assert 'fingerprint' in first['metadata']
	assert first['metadata']['fingerprint'] == fp
```

3) `tests/test_vector_db_query.py` (skeleton)
```py
def test_retrieve_chunks(monkeypatch):
	# stub a chroma collection's query return
	fake_query_result = {'documents': ['doc1'], 'metadatas': [{'fingerprint':'abc'}], 'distances':[0.1]}
	class FakeCollection:
		def query(self, *args, **kwargs):
			return fake_query_result

	monkeypatch.setattr('rag_kmk.vector_db.get_collection', lambda *a, **k: FakeCollection())
	from rag_kmk.vector_db import retrieve_chunks
	out = retrieve_chunks('test query')
	assert isinstance(out, list)
	assert out[0]['metadata']['fingerprint'] == 'abc'
```

Fixtures example (put in `tests/conftest.py`)
```py
import pytest

@pytest.fixture
def fake_chat_client():
	class C:
		def generate(self, prompt, **opts):
			return 'fake'
		def close(self):
			pass
	return C()

@pytest.fixture
def fake_chroma_collection():
	class Col:
		def __init__(self):
			self._count = 0
		def add(self, *args, **kw):
			self._count += 1
		def count(self):
			return self._count
		def query(self, *a, **k):
			return {'documents': [], 'metadatas': []}
	return Col()
```


Phase 4 — LLM wrapper resilience and testing (medium priority)
- Implement a thin `llm_wrapper` around the chat client used by `generate_LLM_answer` to add:
	- Retry with exponential backoff on transient errors (e.g., `RuntimeError` that contains 'client has been closed').
	- A non-network, testable interface for `generate(prompt, context)` that can be stubbed in tests.
- Replace `get_API_key()` or plain `.env` parsing with `python-dotenv` or `pydantic-settings` helpers.
 - Be explicit about fixing brittle .env parsing: replace any ad-hoc `if 'GEMINI_API_KEY' or 'GOOGLE_API_KEY' in line:` checks with proper dotenv parsing (python-dotenv or pydantic-settings) and raise `MissingAPIKey` when appropriate.

Acceptance criteria (Phase 4)
- Unit test: simulate `build_chatBot` returning a client that raises `RuntimeError('client has been closed')` on first call and succeeds on retry; assert `generate_LLM_answer` returns the expected value.
- Unit test: missing API key raises `MissingAPIKey`.

Phase 5 — Tests, docs, and CI (medium priority)
- Add unit tests in `tests/` for new behaviors and convert some higher-level tests to use mocks rather than real LLM/chroma.
- Add `tests/test_cli_smoke.py` (integration-like unit test) that runs `run.main(['--smoke', '--docs', 'tests/sample_documents'])` with `build_chatBot` and `build_knowledge_base` patched to return test doubles.
- Update `README.md` with programmatic usage examples and CLI usage examples.

- Add the specific unit test files called out in the repository TODO:
	- `tests/test_llm_interface_retry.py` — simulate transient runtime errors and assert retry/backoff logic.
	- `tests/test_document_loader_branches.py` — cover txt/pdf/docx handling, empty file behavior, and metadata population.
	- `tests/test_vector_db_query.py` — mock chroma collection `.query()` return shapes and assert `retrieve_chunks`/`show_results` behavior.

Acceptance criteria (Phase 5)
- `pytest -q` runs and all new tests pass locally (no external network required).
- CI (if configured later) will run `pytest --maxfail=1` and get green.

Branch, commit, and changelog rules for automated agents
- Create a feature branch per phase: `feature/phase-1-import-hygiene`, `feature/phase-2-cli`, etc.
- Keep commits small and focused (one logical change per commit). Example commit title: `phase-1: move build_chatBot to builder and stop import-time init`.
- Update `CHANGELOG.md` with a one-line entry per merged phase, prefixed with the phase number.

Other small clarifications
- Config example (add to `docs/` or reuse existing `config/config.yaml`):
```yaml
llm:
	provider: gemini
	api_key_env_var: GEMINI_API_KEY
	model: gemini-2.5-flash
chroma:
	path: ./chroma_db
```
- For `--smoke` define "summary created" as `summarize_collection` returning a non-empty summary dict or list; tests should patch `summarize_collection` to return `{'summary': 'ok'}` and assert the CLI exits 0 and prints/logs the summary at INFO level.
- Ensure tests run without network by default: set env var `RAG_KMK_TEST=1` in test sessions or rely on pytest monkeypatch to replace any network calls.


Implementation details and rules for the coding agent
---------------------------------------------------
- Make small commits; keep changes confined to a few files per commit. Prefer conservative edits.
- For any change that may affect public API, add a short note in `CHANGELOG.md` (create one if missing).
- When adding tests:
	- Use pytest fixtures in `tests/conftest.py` where helpful (e.g., sample KB, fake LLM client).
	- Avoid network calls — use monkeypatch or pytest `mocker` to stub external dependencies.
- Logging: add `logger = logging.getLogger(__name__)` to modules and use `logger.debug/info/warning/error` accordingly.
- Config: add a `rag_kmk/config.py` helper that provides `load_config(path=None)` and `mask_config()`.

Quick developer checklist (for each phase)
-----------------------------------------
- Run tests after each small change: `pytest -q`.
- Validate imports do not trigger side-effects: `python -c "import rag_kmk; print('ok')"`.
- For CLI behavior: run `python run.py --smoke --docs tests/sample_documents` (or the patched test equivalent).

Deliverable format
------------------
When you finish a phase, produce:
1) Code changes (commits) limited to the files required.
2) One or more tests demonstrating the change (pytest).
3) Short release note appended to `CHANGELOG.md` describing the change and why.
4) A short summary message listing what you changed, tests run, and whether CI would pass locally.

If you get blocked
------------------
- If you cannot implement a change due to a missing dependency or environment limitation, add a clear note in `ISSUES.md` describing the blocker and provide a minimal repro and suggested workaround.
- If a test unexpectedly fails, run it locally, capture the failure, attempt a fix (up to 3 tries), and if still failing, record the failure details and proposed remediations in your commit message.

End of prompt

