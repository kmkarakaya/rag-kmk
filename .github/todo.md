
# RAG-KMK code review notes (auto-generated)

This file is a compact, prioritized review of the repository's RAG implementation based on a walkthrough starting from `run.py` and the package entry points. It lists observations (useless or risky code), missing or incorrect RAG pieces, and recommended, actionable next steps (with small code changes and tests).

---

## Quick summary
- The project already implements the main RAG phases (ingest -> index -> retrieve -> generate) but the codebase mixes library initialization, side-effectful imports, and interactive CLI in ways that make it fragile for reuse, testing, and CI.
- Key problem areas: package-level side effects on import, `chat_flow` building a live LLM client at import time, `run.py` mixing orchestration and interactive I/O, and incomplete test coverage for important branches.

---

## Findings (from `run.py` and related modules)

1) Useless / questionable code (easy wins)
  - `rag_kmk/chat_flow/__init__.py` calls `RAG_LLM = build_chatBot()` at import time. This forces API-key validation and network calls on import. Move this out of `__init__`.
  - `rag_kmk/__init__.py` calls `initialize_rag("./config.yaml")` at import time. Importing the package should not perform I/O or load configs by default; provide an explicit `initialize_rag()` call for consumers.
  - `run.py` does `RAG_LLM = build_chatBot()` after already importing `RAG_LLM` from the package — duplicated and confusing.
  - Several large print/debug statements in library modules (e.g., `document_loader.py`, `text_splitter.py`, `database.py`) are helpful during development but should be behind a logger or debug flag.
  - Commented-out code snippets in `run.py` (multiple `build_knowledge_base` variants) should be replaced by CLI flags (e.g., `--index-only`, `--use-persistent-db`) or removed.

2) Missing / incorrect RAG implementations
  - No explicit 'index-only' or 'ingest-only' CLI modes in `run.py`. Useful for CI and batch processing.
  - Lack of deduplication or duplicate-document detection before insertion into the vector DB. Repeated runs may create duplicate vectors.
  - No consistent metadata strategy: `add_meta_data` adds `document` and `category` only — consider adding `source_path`, `created_at`, `sha256` to support provenance and deduplication.
  - `llm_interface` mixes interactive helpers (input, exit()) and library functions; `get_API_key()` uses `exit()` which is not appropriate in a library function.
  - `generateAnswer` concatenates prompt+context in a simple way. Consider template-based prompt assembly and sanitization; also avoid sending overly long contexts without truncation.
  - No rate limiting, batching, or retry/backoff wrapper around LLM calls (other than the small 'client has been closed' retry). Consider a thin wrapper for resilient LLM calls.

3) Bugs / fragile behavior / risks
  - Initialization side effects: importing packages triggers config loads and LLM client creation -> surprising behavior in tests/CI.
  - `create_chroma_client` may return `MISSING_PERSISTENT` when no persistent path is provided; some code paths assume a non-None client/collection. Tests account for this but production code needs clearer error handling.
  - `check_env_file()` in `llm_interface` uses ``if 'GEMINI_API_KEY' or 'GOOGLE_API_KEY' in line:`` which always evaluates truthy; parsing .env lines is brittle — use python-dotenv or robust parsing.
  - Some broad excepts swallow exceptions without logging details; prefer targeted exceptions and logging the stack for debugging.

4) Testing gaps (high priority)
  - `rag_kmk/chat_flow/llm_interface.py` has almost zero coverage; we should add tests for: API-key handling (mocked), `generate_LLM_answer` retry logic, and `generateAnswer` (already covered by a basic test but expand for edge cases).
  - `knowledge_base/document_loader.py` has many untested branches (docx handling, errors, empty files). Add tests using sample files and mocks for `docx2txt`.
  - `vector_db/query.py` is nearly untested; add tests that simulate a chroma collection's `query()` return value and verify `retrieve_chunks`/`show_results` behavior.

---

## Recommended immediate fixes (low-risk, high-impact)

1) Remove side effects from package imports
	- Change `rag_kmk/__init__.py` to not call `initialize_rag()` on import. Export `initialize_rag()` and lazily load config when called.
	- Remove `RAG_LLM = build_chatBot()` from `rag_kmk/chat_flow/__init__.py`. Export `build_chatBot` and let callers decide when to instantiate the chat object.

2) Improve `run.py` into a clear orchestrator CLI
	- Replace commented fragments with CLI flags: `--index-only`, `--index-path PATH`, `--use-persistent-db`, `--model MODEL`, `--smoke`.
	- Move interactive loop to a dedicated `run_interactive()` function and invoke it only if not in `--smoke` mode.
	- Avoid mutating module-level `CONFIG` without an explicit CLI option; instead, use a local copy or accept `--model` flag.

3) Strengthen configuration and secrets handling
	- Replace brittle `.env` parsing with `python-dotenv` or `pydantic-settings` (already available in your env). Do not call `exit()` from library functions; raise exceptions and let the CLI handle termination.

4) Small but important code hygiene
	- Replace prints with `logging` (configurable level). Add a small `logger = logging.getLogger(__name__)` to modules.
	- Tighten exception handling; log full exception on unexpected failures.

---

## Medium-term improvements (nice-to-have)

- Add an 'indexing' step that computes fingerprints (sha256 of file) and stores them in metadata to avoid duplicate indexing.
- Add an ingestion queue or batch processing mode for large document sets.
- Add prompt templates with a prompt length guard and context truncation by token count.
- Add an integration test that runs the full smoke pipeline in a reproducible, non-interactive mode (use `--smoke`).

---

## Concrete next steps (actionable checklist)

1. [High] Stop running side-effects at import:
	- Edit `rag_kmk/__init__.py` to remove auto `initialize_rag()` and export function only.
	- Edit `rag_kmk/chat_flow/__init__.py` to remove auto `build_chatBot()` and export `build_chatBot` only.

2. [High] Harden `llm_interface`:
	- Replace `.env` parsing with python-dotenv parsing; raise a custom `MissingAPIKey` exception instead of exit.
	- Add unit tests for `generate_LLM_answer` retry behavior (simulate httpx RuntimeError containing 'client has been closed').

3. [High] Improve `run.py` CLI
	- Implement explicit flags: `--index-only`, `--index-path`, `--use-persistent-db`, `--model`, `--smoke`.
	- Move interactive loop into a separate function and guard it behind `--smoke`.

4. [High] Tests to add (priority order):
	- `test_llm_interface_retry.py` — simulate RuntimeError and assert retry.
	- `test_document_loader_branches.py` — test pdf/docx/txt paths and error handling.
	- `test_vector_db_query.py` — test `retrieve_chunks` and `show_results` with fake query responses.

5. [Medium] Add deduplication by file fingerprint and add provenance metadata (source path, created_at, fingerprint).

6. [Medium] Add CI job (GitHub Actions) that installs `requirements_dev.txt` and runs `pytest --cov` and uploads `htmlcov` artifact.

---

## Suggested immediate code edits I can implement now (pick any)
- Remove package-import side effects (two small edits).
- Add `--index-only` / `--smoke` flags to `run.py` and reorganize orchestration into small functions.
- Add a unit test for `generate_LLM_answer` retry logic.

If you want, tell me which one to implement first and I will apply the change and run tests.

---

Signed-off-by: automated-review (assistant)

---

## Review of `run.py` (file: `run.py`) — findings and recommendations

Summary: `run.py` currently acts as a thin orchestrator but mixes library import-time side-effects, global mutation of package-level `CONFIG`, interactive behaviour, and duplicated LLM client construction. Below are concrete observations grouped by category and recommended next steps.

1) Useless or questionable code (easy wins)
  - Top-level import: `from rag_kmk.chat_flow import ... RAG_LLM ...` imports a symbol that should not be created at import-time. It increases fragility by forcing side-effects when `rag_kmk` is imported. Remove importing `RAG_LLM` directly; construct the client inside `main()`.
  - Duplicate LLM build: `RAG_LLM = build_chatBot()` is called in `run.py` even though the module imports `RAG_LLM` at top — confusing and redundant.
  - Large, unguarded prints: `print("--------------------- ORIGINAL CONFIG ---------------------\n", CONFIG['llm'])` prints the live `CONFIG`, which may contain secrets; prefer `logging.debug()` and avoid printing secrets.
  - Global `CONFIG` mutation: `CONFIG['llm'].update({'model': 'gemini-2.5-flash'})` mutates package-level config on import/runtime. That surprises callers and makes testing harder. Use a local copy or a CLI flag to set model.
  - Commented code blocks: multiple `build_knowledge_base` variants are commented out. Replace with CLI flags (e.g., `--index-only`, `--use-persistent-db`) or remove dead code.

2) Missing or incorrect RAG implementation steps
  - Missing CLI modes: No explicit `--index-only`/`--ingest-only` or `--query-only` flags. Those are useful for batch indexing and CI smoke tests.
  - No deduplication/provenance: `build_knowledge_base` is used as-is; `run.py` doesn't compute/document fingerprints (sha256), source_path, or created_at metadata before indexing. That allows duplicate vectors across repeated runs.
  - Interactive vs library separation: `run_rag_pipeline(RAG_LLM, knowledge_base)` is invoked directly. If `run_rag_pipeline` expects to run interactive loops or call `input()`, the top-level script mixes interactive flows with batch modes. Provide a `--smoke` (exists) and also `--no-interactive` and `--non-interactive` conventions. Prefer `run_interactive()` as a separate function.
  - No model selection guard: The code silently sets the model to `gemini-2.5-flash`. This should be controlled through CLI (`--model`) or environment config, with validation and fallbacks.

3) Bugs / fragile behavior / risks observed related to RAG
  - Import-time side effects: `run.py` imports package-level objects which may trigger top-level initialization in the library (see `rag_kmk/__init__` and `rag_kmk/chat_flow/__init__` in repo review). This causes network calls or API-key checks on import. Make package imports side-effect free.
  - Hard-coded file paths: `document_directory_path=r'.\tests\sample_documents'` is fine for local development but should be parameterized via `--docs`/`--path` CLI arg.
  - Exception handling and logging: `run.py` prints status and uses value enums from `build_knowledge_base` but doesn't inspect error causes when indexing fails. Add structured logging and explicit exit codes.

4) Recommended immediate edits (non-breaking, low risk)
  - Remove `RAG_LLM` import from `from rag_kmk.chat_flow import ...` at module top; import only functions and types. Build the LLM client with `build_chatBot()` inside `main()` and keep it local.
  - Replace direct `CONFIG` mutation with a local copy: e.g., `local_config = deepcopy(CONFIG); local_config['llm']['model'] = args.model` or apply the option only when `--model` is set.
  - Add CLI flags: `--index-only`, `--docs PATH`, `--chroma-path PATH`, `--model MODEL`, `--use-persistent-db`, `--no-interactive`. Wire them to `build_knowledge_base` and `run_rag_pipeline`.
  - Convert prints to `logging` (configure level from CLI `--debug`). Avoid logging secrets.
  - Provide `run_interactive(RAG_LLM, knowledge_base)` separate from `run_rag_pipeline` so smoke and batch runs skip interactive prompts.

5) Tests and verification
  - Add a smoke test that runs `run.py --smoke` in CI using a small sample documents folder; assert it creates/uses a temporary collection and exits without prompting.
  - Add unit tests for `build_chatBot()` creation failure modes and for `run_rag_pipeline()` non-interactive behavior (mock LLM calls).

6) Small proactive extras (optional but recommended)
  - Add a `--dry-run` that performs indexing discovery but does not write to DB (useful for CI validation of discovery/metadata generation).
  - When ingesting documents, compute a fingerprint (sha256) and include metadata keys `source_path`, `created_at`, `fingerprint` on each chunk/document to make deduplication and provenance possible.

Concluding note: `run.py` is a good single-file orchestrator for local flows, but it currently relies on a library that performs initialization at import-time and mutates package-level config. The minimal next change is to stop importing `RAG_LLM` (or other side-effectful symbols) at module level and add a few CLI flags to control model and modes. See recommended immediate edits above — these are small, low-risk, and will make the package robust for use as a library and CLI.

---

## Step-by-step walkthrough of `run.py` (detailed)

I'll go through `run.py` in code-order and annotate each logical block with: what it does, why it's a risk or incorrect for a library/CLI, and an exact suggested change (including small code examples) and tests to validate the change.

File head (imports + module-level):

```py
#pip install rag-kmk
# ensure that you have a directory ./files with some documents in it.
from  rag_kmk import CONFIG
from rag_kmk.knowledge_base import build_knowledge_base   
from rag_kmk.vector_db import summarize_collection, retrieve_chunks, show_results
from rag_kmk.chat_flow import generateAnswer, generate_LLM_answer, RAG_LLM, run_rag_pipeline, build_chatBot
import argparse
```

- What it does: imports package-level `CONFIG`, functions from `knowledge_base` and `vector_db` and multiple symbols from `chat_flow`, including `RAG_LLM` which appears to be an instantiated client.
- Why risky: importing `RAG_LLM` at module scope likely triggers side effects (API key checks, network/LLM client creation). Library imports should be side-effect free.
- Exact fix:
  - Remove `RAG_LLM` from top-level imports. Only import the builder `build_chatBot` and functions you need. Build the client inside `main()` where you can handle errors and CLI options.
  - Example change (in `run.py`):

```py
from rag_kmk.chat_flow import generateAnswer, generate_LLM_answer, run_rag_pipeline, build_chatBot
```

- Tests to validate:
  - Run `python -c 'import rag_kmk; print("import ok")'` before and after to ensure no network/API validation happens on import.
  - Unit test: import `run` module and assert it does not attempt to read env or make network calls (use monkeypatch to ensure build_chatBot isn't called on import).

Main and argparse:

```py
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--smoke', action='store_true', help='Run non-interactive smoke pipeline and exit')
    args = parser.parse_args()
```

- What it does: creates a single `--smoke` flag (useful). Good start but minimal.
- Why risky: lack of other flags makes the script inflexible (no `--docs`, `--model`, `--index-only`). Also `parser.parse_args()` reads sys.argv early; it's fine here but better to allow passing args in tests.
- Exact fix:
  - Add flags: `--docs` (path), `--chroma-path`, `--index-only`, `--model`, `--no-interactive` (alias), `--debug`.
  - Prefer `parser.parse_args(args)` in a wrapper so tests can call main with custom args.

- Tests to validate:
  - Add unit tests for `main(['--smoke'])`, `main(['--index-only','--docs','tests/sample_documents'])` verifying behavior without requiring interactive input.

CONFIG printing and mutation:

```py
    print("--------------------- ORIGINAL CONFIG ---------------------\n", CONFIG['llm'])
    CONFIG['llm'].update({'model': 'gemini-2.5-flash'})
    print("--------------------- AFTER CONFIG UPDATE ---------------------\n", CONFIG['llm'])
```

- What it does: prints the `CONFIG['llm']` and mutates the global `CONFIG` by forcibly setting the model.
- Why risky: `CONFIG` may contain secrets (API keys). Mutating package-level config is surprising and breaks test isolation and other consumers. Hard-coding a provider model here is unexpected.
- Exact fix:
  - Replace prints with logging and avoid dumping full CONFIG. If needed, log masked values.
  - Do not mutate `CONFIG` directly. Create a local copy and apply runtime overrides only when user passes `--model`.
  - Example change:

```py
import copy, logging
logger = logging.getLogger(__name__)

local_config = copy.deepcopy(CONFIG)
if args.model:
    local_config['llm']['model'] = args.model
logger.info('Using LLM model: %s', local_config['llm'].get('model'))
```

- Tests to validate:
  - Unit test that `CONFIG` is unchanged after calling `main()` with `--model`.
  - Ensure logs do not contain full API keys (masking test).

LLM client construction and global override:

```py
    global RAG_LLM
    RAG_LLM = build_chatBot()
```

- What it does: builds the chat bot and stores it into a global name `RAG_LLM` (possibly overwriting the one imported earlier).
- Why risky: global mutation makes flow harder to reason about. If `build_chatBot()` fails, the script may crash without helpful messaging. The `build_chatBot()` function should accept config and return a client; the script should handle exceptions and provide clear error messages.
- Exact fix:
  - Create the client in a local variable, handle exceptions, and pass it explicitly to functions that need it. Do not use `global`.
  - Example:

```py
try:
    rag_llm = build_chatBot(local_config['llm'])
except Exception as e:
    logger.exception('Failed to build LLM client: %s', e)
    return 2

# pass rag_llm where needed
```

- Tests to validate:
  - Unit test where `build_chatBot` is patched to raise and assert `main()` returns non-zero code and logs the exception.

Knowledge base build comments and usage:

```py
    # Load the existing chromadb collection and add new documents to it
    #knowledge_base, chromaDB_status = build_knowledge_base(document_directory_path=r'.\tests\sample_documents', chromaDB_path=r'.\chroma_db')

    # Load the existing chromadb collection without adding new documents
    #knowledge_base, chromaDB_status = build_knowledge_base( chromaDB_path=r'.\chroma_db')

  # Create a new temporary ChromaDB collection (persistent directory) and add new documents to it
    knowledge_base, chromaDB_status = build_knowledge_base( document_directory_path=r'.\tests\sample_documents')
```

- What it does: shows example use cases, but the chosen one is hard-coded to use sample documents folder.
 - Why risky: commented examples are not discoverable via CLI. The script previously demonstrated an implicit in-memory collection path; that behavior has been removed and callers should provide an explicit `--chroma-path` or use a temporary directory. There's no clear `--index-only` or `--chroma-path` argument.
- Exact fix:
  - Wire `build_knowledge_base` to CLI flags. For example, if `--chroma-path` provided, call with `chromaDB_path`; if `--docs` set, pass `document_directory_path`.
  - Add an `--index-only` flag that runs `build_knowledge_base` and exits after summarizing.

- Tests to validate:
  - Unit test `main(['--index-only','--docs','tests/sample_documents'])` and assert that `build_knowledge_base` was called with correct args (use monkeypatch).

Status printing and configuration dump:

```py
    print("--------------------- CHROMADB STATUS ---------------------\n", chromaDB_status.value)
    print("-----------------"*4)
    print(CONFIG)

    print("-----------------"*4)
```

- What it does: prints DB status and dumps global `CONFIG` again.
- Why risky: again, `CONFIG` may contain secrets; noisy prints complicate production runs.
- Exact fix:
  - Use `logger.info` to record status and avoid dumping `CONFIG`. If a full dump is desired, implement a `mask_secrets()` helper and log the masked config under debug.

- Tests to validate:
  - Test that when `--smoke` is used the code logs status and exits; assert logs contain status string but not API keys.

Summarize collection and interactive pipeline:

```py
    if knowledge_base:
        summarize_collection(knowledge_base)
        if args.smoke:
            print('Smoke mode: exiting after summary')
            return
        run_rag_pipeline(RAG_LLM,knowledge_base)
    else:
        print("No documents loaded.")
```

- What it does: summarizes the collection, respects `--smoke` by exiting after summary; otherwise runs `run_rag_pipeline` with `RAG_LLM`.
- Why risky: `run_rag_pipeline` receives `RAG_LLM` as a global which might not be constructed or might come from the module import. The function probably opens interactive input() and will block in non-interactive contexts.
- Exact fix:
  - Ensure `run_rag_pipeline` receives the explicit `rag_llm` local client variable.
  - If `run_rag_pipeline` is interactive, add a non-interactive counterpart or pass a `non_interactive=True` flag to it so the pipeline can run in deterministic, testable ways.

- Tests to validate:
  - Unit test that calls `run_rag_pipeline` with a mocked LLM client and a fake knowledge base to assert the function calls the LLM for generation but does not call `input()` when invoked with `non_interactive=True`.

Top-level guard:

```py
if __name__ == "__main__":
    main()
```

- What it does: standard. Keep as-is but ensure `main()` returns an exit code and use `sys.exit(main())` in the future for meaningful process exit codes.
- Exact fix:
  - Change to `if __name__ == "__main__": import sys; sys.exit(main())` and make `main()` return an integer code (0 success, non-zero failure).

- Tests to validate:
  - Run `python run.py --smoke` in CI stub and assert the process exit code is 0.

Consolidated patch suggestions (minimal, safe):

1) `run.py` imports: remove `RAG_LLM` from top-level imports.
2) Parse more CLI args: add `--docs`, `--chroma-path`, `--index-only`, `--model`, `--no-interactive`, `--debug`.
3) Do not mutate `CONFIG` in-place; use a `local_config = deepcopy(CONFIG)`.
4) Build LLM client locally with try/except and pass it explicitly to `run_rag_pipeline`.
5) Replace prints with `logging` and mask `CONFIG` when logging.
6) Have `main()` return an exit code and call `sys.exit(main())` in the guard.

Quick example: minimal `run.py` skeleton after edits

```py
import argparse, copy, logging, sys
from rag_kmk import CONFIG
from rag_kmk.knowledge_base import build_knowledge_base
from rag_kmk.chat_flow import build_chatBot, run_rag_pipeline

logger = logging.getLogger(__name__)

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--docs')
    parser.add_argument('--model')
    parser.add_argument('--index-only', action='store_true')
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args(argv)

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    local_config = copy.deepcopy(CONFIG)
    if args.model:
        local_config['llm']['model'] = args.model

    try:
        rag_llm = build_chatBot(local_config['llm'])
    except Exception as e:
        logger.exception('LLM init failed')
        return 2

    kb, status = build_knowledge_base(document_directory_path=args.docs) if args.docs else build_knowledge_base()
    if not kb:
        logger.info('No documents loaded')
        return 0

    summarize_collection(kb)
    if args.index_only or args.smoke:
        return 0

    run_rag_pipeline(rag_llm, kb, non_interactive=not sys.stdin.isatty())
    return 0

if __name__ == '__main__':
    sys.exit(main())
```

Follow-up tasks after making these edits:
- Update `rag_kmk/chat_flow/__init__.py` to avoid instantiating `RAG_LLM` at import time.
- Add tests: `test_run_smoke.py`, `test_run_index_only.py`, `test_main_handles_llm_failures.py`.
- Add a small helper `mask_config_secrets()` in `rag_kmk/config` to safely log config in debug mode.

---

Progress update:
- Marked the `Refactor run.py into clear CLI` todo as in-progress.
- Appended this detailed, line-by-line `run.py` walkthrough to `.github/todo.md` with exact code suggestions and tests.

What's next if you want me to continue (pick one):
- Implement the minimal `run.py` skeleton in-place (safe). I'll change `run.py` to the pattern above, run tests, and report results.
- Or edit `rag_kmk/chat_flow/__init__.py` to remove the import-time `build_chatBot()` call (this is higher-impact but recommended next).

---

## Library-focused review and recommended API/design changes

Context: `run.py` is an example CLI showing how you expect consumers to use the `rag_kmk` library. From that example we can infer the public contract the library should offer and the improvements needed to make the library reliable for programmatic use (not just as a script). The list below translates the `run.py` findings into library-level recommendations, API contracts, and tests.

1) Public API contracts (what the library should expose)
  - build_chatBot(config: dict) -> ChatClient
    - Inputs: validated config dictionary (provider, model, credentials). Do NOT read environment or files inside this function; require config or use a helper `load_config()`.
    - Outputs: a minimal ChatClient interface with methods: `generate(prompt, **opts)`, `close()` and property `supports_streaming`.
    - Error modes: raise well-defined exceptions (e.g., `MissingAPIKey`, `LLMInitError`) on invalid/failed init.

  - build_knowledge_base(document_directory_path: Optional[str]=None, chromaDB_path: Optional[str]=None, persist: bool=False, metadata_strategy: Optional[callable]=None) -> Tuple[KnowledgeBase, Status]
    - Inputs: paths and flags; metadata_strategy is a callable that returns metadata for a given document (for fingerprints and provenance).
    - Outputs: KnowledgeBase object (with controlled API) and status enum.
    - Error modes: return None or raise `IndexingError` for non-recoverable problems; prefer raising in library mode and returning status codes in CLI mode.

  - run_rag_pipeline(chat_client: ChatClient, knowledge_base: KnowledgeBase, non_interactive: bool=False) -> None
    - Inputs: explicit client and KB. Must not rely on global state. If interactive, separate into `run_interactive()`.
    - Error modes: raise `GenerationError` on LLM failures after retries.

  - vector DB helpers: summarize_collection(kb), retrieve_chunks(kb, query, top_k=5) -> list
    - Return pure data structures (lists/dicts) not prints.

2) Metadata & dedup strategy (required for robust indexing)
  - Standardize metadata keys on ingestion: `source_path`, `created_at` (ISO8601), `fingerprint` (sha256 hex), `document` (filename), `category`.
  - Implement `compute_fingerprint(path) -> str` used before tokenization. Use file bytes -> sha256.
  - Before indexing, check for existing fingerprint in metadata and skip duplicates when `persist=True`. Store fingerprints in chroma metadata to support dedup.

3) Exceptions and error modes
  - Replace `exit()` calls in library code with exceptions: `MissingAPIKey`, `InvalidConfig`, `LLMInitError`, `IndexingError`, `GenerationError`.
  - CLI entrypoints (like `run.py`) should catch these exceptions and translate to user-friendly messages and exit codes.

4) Config and secrets handling
  - Provide `load_config(path: Optional[str]=None) -> dict` to load config from file and environment using `python-dotenv` or `pydantic-settings`.
  - Hide secrets in logs by providing `mask_config(config, keys=('api_key','secret','token'))`.

5) Testing plan (priority)
  - Unit tests for `build_chatBot`:
    - Success path with a fake/local stub client.
    - Failure path: missing key -> assert `MissingAPIKey` raised.

  - Unit tests for `build_knowledge_base`:
    - Ingest txt/pdf/docx (use sample files) and assert metadata keys present and fingerprint computed.
    - Dedup test: index same file twice with `persist=True` and assert second run does not add new vectors.

  - Unit tests for `run_rag_pipeline`:
    - Non-interactive mode: patch ChatClient.generate, assert it's called with expected prompt and context.
    - Interactive mode: patch `input()` to simulate user prompts and assert flows proceed.

  - Integration smoke test: `tests/test_cli_smoke.py` runs `run.py --smoke --docs tests/sample_documents` in a subprocess and asserts exit code 0 and that a summary is created.

6) Developer ergonomics & docs
  - Update README with explicit examples for programmatic usage (import paths and minimal example using returned ChatClient and KnowledgeBase objects).
  - Provide a `quickstart.py` snippet showing: load_config -> build_knowledge_base -> build_chatBot -> run_rag_pipeline(non_interactive=True).

7) Small, safe dev tasks to implement now (priority order)
  - (High) Make `build_chatBot` accept config and stop constructing LLM at import time. Update `rag_kmk/chat_flow/__init__.py` to export builder not instance.
  - (High) Add `compute_fingerprint` and wire into `build_knowledge_base` metadata pipeline.
  - (High) Add exceptions module: `rag_kmk/exceptions.py` with the recommended exception classes.
  - (Medium) Add `mask_config` helper and use logging instead of prints across modules.

Closing: these library-focused changes will make `rag_kmk` usable as a programmatic library, easier to test, and safer to run in CI. I can implement the small, safe high-priority edits next (for example: remove import-time `RAG_LLM` and add `compute_fingerprint`) — tell me which you prefer and I'll apply the changes and run tests.

