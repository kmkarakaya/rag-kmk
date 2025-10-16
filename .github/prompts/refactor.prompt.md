Refactor task: create load_knowledge_base() and narrow build_knowledge_base() responsibility in #file:document_loader.py and #file:database.py

Goal
----

The repository currently has a function named `build_knowledge_base()` that both opens/creates a persistent ChromaDB collection and optionally ingests documents from a folder. This has caused confusion and misuse: callers sometimes want a simple create-and-ingest operation (always create a new collection from a folder) while other callers want to load an existing collection without performing ingestion. The goal of this refactor is to split those responsibilities clearly.

High-level change
-----------------

- Introduce a new function `load_knowledge_base(collection_name: str, cfg: Optional[dict] = None) -> Tuple[Optional[Collection], ChromaDBStatus]` that loads (opens) an existing persistent ChromaDB collection. It should mirror the current "open existing" behavior in `build_knowledge_base()` (including robust status handling such as MISSING_PERSISTENT, MISSING_COLLECTION, ERROR), but must NOT create new persistent folders or collections. It must NOT ingest documents.
- Narrow `build_knowledge_base()` semantics: it should become the explicit "create and ingest" operation. Its contract will be: create a new persistent ChromaDB collection (fail if collection already exists), then ingest documents from a provided folder into the new collection. It should accept a required `document_directory_path` when used for create+ingest and return the (collection, status) pair on success or an error status otherwise.

Detailed function contracts
---------------------------

1) load_knowledge_base

- Signature: load_knowledge_base(collection_name: str, cfg: Optional[dict] = None) -> Tuple[Optional[Any], vdb_database.ChromaDBStatus]
- Behavior:
  - Read `vector_db.chromaDB_path` from config (cfg overrides load_config()).
  - If the configured `chromaDB_path` is missing/empty, return ERROR or raise ValueError (match existing project conventions).
  - Do NOT attempt to create the persistent directory. If the path does not exist, return MISSING_PERSISTENT.
  - Call the DB factory `vdb_database.create_chroma_client()` with create_new=False (or equivalent). Handle the returned tuple formats like current code (client/collection/status or collection/status).
  - Propagate statuses: return MISSING_COLLECTION, MISSING_PERSISTENT, ALREADY_EXISTS only where they are meaningful for the "load" operation (ALREADY_EXISTS should not be treated as an error for load — but the factory may not return it when create_new=False).
  - Do not ingest documents or call load_and_add_documents(). Return the opened collection and status on success.
  - Provide clear printed/logged messages for success and error cases; mirror existing messaging used by build_knowledge_base() but without create semantics.

2) build_knowledge_base (re-scoped)

- Signature: build_knowledge_base(collection_name: str, document_directory_path: str, cfg: Optional[dict] = None, overwrite: bool = False) -> Tuple[Optional[Any], vdb_database.ChromaDBStatus]
- Behavior:
  - Must be explicit about its purpose: create a new persistent collection and ingest documents from `document_directory_path`.
  - Read `vector_db.chromaDB_path` from config; create the persistent folder if needed.
  - If the collection already exists and `overwrite` is False, return ALREADY_EXISTS and do not ingest.
  - If overwrite is True, fail-fast or document the destructive behavior (implementation may require DB-admin operations; if destructive overwrite isn't feasible, document that caller must delete first and return ALREADY_EXISTS).
  - On success (collection created and ingestion performed), return the collection and status.
  - Must call `load_and_add_documents()` to ingest documents from the directory. If ingestion is requested but `document_directory_path` is missing, return an error status and do not create the collection.

Edge cases and error handling (apply to both functions)
-------------------------------------------------------

- Config missing/invalid: if `vector_db.chromaDB_path` is not set or invalid, raise ValueError or return ERROR consistent with existing code style.
- Path non-existent: `load_knowledge_base()` returns MISSING_PERSISTENT; `build_knowledge_base()` with create semantics will create the directory (or return ERROR if creation fails).
- Document directory validation: when ingesting, validate the directory exists and is readable; return informative status when ingestion is skipped.
- Return values: keep compatibility with existing callers expecting (collection, chroma_status). Use vdb_database.ChromaDBStatus enum values.

Acceptance criteria / tests
---------------------------

- Add tests (or update existing tests) to cover:
  - `load_knowledge_base()` returns MISSING_PERSISTENT when the configured chromaDB path doesn't exist.
  - `load_knowledge_base()` opens an existing collection successfully and does not call ingestion.
  - `build_knowledge_base()` creates a new collection and ingests documents when provided a valid `document_directory_path`.
  - `build_knowledge_base()` returns ALREADY_EXISTS when attempting to create an already-existing collection (unless overwrite True and destructive behavior is supported).
  - Document ingestion errors are surfaced in the returned status or separate ingestion results as appropriate.

Implementation guidance
-----------------------

- Prefer minimal code changes: implement `load_knowledge_base()` by extracting the opening-only branches from the existing `build_knowledge_base()`.
- Keep existing logging and user-facing messages where they map to load vs create semantics; remove or update messages that imply creation when not applicable.
- Keep `build_knowledge_base()` name and behavior only for create+ingest to minimize breaking changes, but update its docstring and signature to make the contract explicit.
- Add unit tests in `tests/` mirroring existing patterns (mock/stub chromadb or vdb_database.create_chroma_client as needed). Follow project testing conventions in `.github/instructions/copilot-instructions.md`.

Example usage
-------------

# Load existing collection (no ingestion)

collection, status = load_knowledge_base('my_collection')

# Create and ingest into a new collection

collection, status = build_knowledge_base('new_collection', r"path\to\documents", overwrite=False)

Notes
-----

- Do not modify `run.py` (project rule). Keep changes confined to library code and tests.
- Use environment-variable driven or mocked DB clients in tests; avoid network or real chromadb dependencies in CI.

Related tests that must be reviewed/updated
-------------------------------------------

The repository tests include a number of tests that currently call `build_knowledge_base()` for both "open existing" and "create+ingest" behaviors. After the refactor these tests will need either to call the new `load_knowledge_base()` when they only intend to open an existing collection, or continue to call `build_knowledge_base()` when they intend to create+ingest. Below is a file-by-file list with notes on the expected update.

- `tests/test_document_loader.py`

  - test_build_knowledge_base_with_mock: calls `build_knowledge_base(document_directory_path=..., chromaDB_path=None)` — this is a create+ingest-style usage; keep it calling `build_knowledge_base()` (no change) if it intends to create an in-memory or persistent DB and ingest.
  - test_build_knowledge_base_create_and_ingest: explicitly creates a persistent DB and ingests — keep calling `build_knowledge_base()` (no change).
  - test_build_knowledge_base_open_existing: currently calls `build_knowledge_base(..., create_new=False, add_documents=False)` to open an existing collection — change this test to call `load_knowledge_base(collection_name=..., cfg=...)` and assert it returns OK (or appropriate existing status). Alternatively, keep the call but update expectations to reflect the new behavior (prefer new API test).
- `tests/test_build_knowledge_base_modes.py`

  - test_mode1_persistent_plus_add: calls `build_knowledge_base(document_directory_path=..., chromaDB_path=...)` — create+ingest; remains `build_knowledge_base()`.
  - test_mode2_persistent_only: first uses `build_knowledge_base()` to create/populate, then calls `build_knowledge_base(document_directory_path=None, chromaDB_path=...)` to load existing collection — change the second call to `load_knowledge_base(collection_name=..., cfg=...)` (or equivalent) to explicitly load without ingestion and assert existing status.
  - test_mode3_inmemory_plus_add: in-memory create+ingest — remains `build_knowledge_base()`.
  - test_load_and_add_documents_public_api: tests `load_and_add_documents()` directly — no change.
- `tests/test_path_resolution_and_force_persistence.py`

  - Many tests here call `build_knowledge_base()` with `create_new=False` and `add_documents=False` to assert path-resolution behavior for loading. Those should be changed to call `load_knowledge_base()` when they only intend to load/open an existing collection. Tests that simulate in-memory behavior via `create_new=True` can continue to use `build_knowledge_base()` for create semantics.
- `tests/test_cli_smoke.py`, `tests/test_run_workflow.py`, `tests/test_run_flow_equivalent.py`, `tests/test_repo_chromadb_smoke.py` and similar integration-style tests

  - These tests call `build_knowledge_base(document_directory_path=...)` to create and ingest a temporary folder of documents before running the rest of the flow — keep these calls as `build_knowledge_base()` since they are create+ingest scenarios.

Recommended test updates
------------------------

- For each test that currently calls `build_knowledge_base()` with `create_new=False` and `add_documents=False`, replace that invocation with `load_knowledge_base(collection_name=..., cfg=...)` and update assertions to expect the same status values the test previously asserted (MISSING_PERSISTENT, MISSING_COLLECTION, OK, etc.).
- Ensure new unit tests are added for `load_knowledge_base()` specifically to assert:
  - MISSING_PERSISTENT when path missing
  - MISSING_COLLECTION when collection missing
  - OK when collection exists
- Use existing test fixtures/mocks that stub `vdb_database.create_chroma_client()` to simulate different statuses; follow the same mocking approach already in tests like `test_document_loader.py` and `test_path_resolution_and_force_persistence.py`.

Repository status and approach
------------------------------

This library is not released yet. It's safe to apply breaking changes directly in the codebase to simplify the API and tests. There is no need for a migration plan for external users. Proceed with implementing `load_knowledge_base()` and updating call sites and tests directly in this repository to reflect the new, clearer API.

Implementation checklist (local only)
-------------------------------------

1. Implement `load_knowledge_base()` and update `build_knowledge_base()` per prompt.
2. Update tests in-place to call `load_knowledge_base()` where appropriate and adjust assertions.
3. Add unit tests for `load_knowledge_base()` to cover the acceptance criteria.
4. Run `pytest` and iterate until tests pass locally.
