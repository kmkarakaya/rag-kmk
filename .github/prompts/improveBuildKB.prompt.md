
Title: Improve build_knowledge_base (minimal, config-driven, explicit intent)

Goal
----
Make small, well-scoped changes to the RAG codebase so the
`build_knowledge_base(...)` call supports four explicit user scenarios:

1. Load an existing persistent ChromaDB collection and add new documents to it.
2. Load an existing persistent ChromaDB collection without adding new documents.
3. Create a new in-memory ChromaDB collection and add new documents to it.
4. Create a new persistent ChromaDB collection and add new documents to it.

Constraints
-----------
- Keep changes minimal and localized. Prefer adding small optional args and
	configuration-driven defaults. Avoid large refactors.
- Favor clarity and explicit intent over implicit behavior inferred from
	parameter presence.
- Use existing `rag_kmk/config/config.yaml` and `rag_kmk/config/config.py` for
	defaults. Do not add new heavy dependencies.

Files to inspect / update
-------------------------
- `rag_kmk/knowledge_base/document_loader.py` (primary)
- `rag_kmk/vector_db/database.py` (to accept create_new and return clear status)
- `run.py` (examples/documentation of usage)
- `rag_kmk/config/config.yaml` and `rag_kmk/config/config.py` (use defaults)

Summary of current behavior
---------------------------
- `build_knowledge_base(document_directory_path=None, chromaDB_path=None, config=None)`
	currently infers behavior solely from presence/absence of `chromaDB_path` and
	`document_directory_path`. This is ambiguous and doesn't allow explicitly
	creating a new persistent DB or skipping document ingestion.

Requested API changes (minimal)
--------------------------------
- Add two optional boolean arguments to `build_knowledge_base`:
	- `create_new: bool = False` — when True, force creation of a new collection
		(in-memory when `chromaDB_path` is None; persistent when `chromaDB_path`
		is provided).
	- `add_documents: bool = True` — when False, skip loading documents even if
		`document_directory_path` is provided.
- Update the call to the vector DB helper `create_chroma_client(...)` so it
	accepts `create_new` and returns a clear `ChromaDBStatus` value indicating
	whether the returned collection is: NEW_MEMORY, EXISTING_PERSISTENT,
	NEW_PERSISTENT, or ERROR.
- Use `config` defaults when arguments are omitted. For example, if
	`chromaDB_path` is None, consult `cfg['vector_db']['chromaDB_path']` before
	assuming in-memory.

Behavior matrix
---------------
Implement behavior so the following matrix holds (explicitly):

| chromaDB_path | create_new | add_documents | outcome |
|---------------|------------|---------------|---------|
| path provided | False      | True/False    | Load existing persistent; optionally add docs |
| path provided | True       | True/False    | Create new persistent at path; optionally add docs |
| None          | True       | True/False    | Create new in-memory; optionally add docs |
| None          | False      | True/False    | Use config chromaDB_path if available; otherwise error/early return |

Implementation details
----------------------
1. document_loader.build_knowledge_base:
	 - Update signature to include `create_new: bool = False, add_documents: bool = True`.
	 - Resolve config early (use provided `config` or `rag_kmk.CONFIG` or
		 `load_config()` from `rag_kmk.config.config`). Extract `vector_db` defaults
		 (collection name, embedding model, chromaDB_path) into local variables.
	 - If `chromaDB_path` arg is None, prefer the value from config's
		 `vector_db.chromaDB_path`. If still None, consider in-memory only when
		 `create_new` is True; otherwise raise a ValueError saying path missing.
	 - Call `vdb_database.create_chroma_client(..., create_new=create_new)`.
	 - Validate the returned `chromaDB_status` against the requested intent and
		 raise/return informative errors if mismatched (e.g., persistent requested
		 but got NEW_MEMORY).
	 - Honor `add_documents`: only call `load_and_add_documents(...)` when
		 `add_documents is True` and `document_directory_path` is provided.
	 - Return `(chroma_collection, chromaDB_status)` as before.

2. vector_db.database.create_chroma_client:
	 - Add optional `create_new=False` parameter, and ensure the function
		 respects it: when `create_new=True` and `chromaDB_path` provided, create a
		 fresh persistent collection (overwrite if necessary or raise if existing —
		 follow minimal safe behavior: create new if not exists; if exists, create
		 a new namespaced collection name using timestamp to avoid destructive
		 behavior unless an explicit `overwrite` flag is added).
	 - Return a clear `ChromaDBStatus` value that covers NEW_MEMORY,
		 EXISTING_PERSISTENT, NEW_PERSISTENT, ERROR. If an enum already exists,
		 extend it accordingly; otherwise add minimal constants.

3. run.py examples:
	 - Update or add commented examples that show how to call the new API for
		 all four scenarios. Keep examples short and inline as comments.

Why config entries are needed / used
-----------------------------------
- `config.yaml` centralizes defaults like `chromaDB_path`, `collection_name`,
	`embedding_model`, and chunk/token settings. Using these ensures consistent
	behavior and allows callers to be concise (pass None and let config supply
	the path).
- `config.py` should be used to load the YAML once and provide a `load_config`
	helper (already present). Callers should prefer `config` param first then
	fallback to module-level `rag_kmk.CONFIG`.

Acceptance criteria (automated checks)
-------------------------------------
1. New function signature in `document_loader.build_knowledge_base` accepts the
	 two new flags and doesn't break existing callers that use the old signature
	 (backwards compatible defaults).
2. `vdb_database.create_chroma_client` accepts `create_new` and returns a
	 `ChromaDBStatus` that can be used to disambiguate NEW_MEMORY vs
	 NEW_PERSISTENT vs EXISTING_PERSISTENT.
3. The code paths for all four scenarios can be executed (use `run.py`
	 commented examples) and they produce expected `ChromaDBStatus` values.
4. Unit tests (minimal) to cover:
	 - Creating an in-memory collection (create_new=True, chromaDB_path=None).
	 - Loading existing persistent collection (create_new=False, path provided,
		 simulate existing).
	 - Creating new persistent collection (create_new=True, path provided).
	 - add_documents=False results in skipping ingestion even if docs exist.

Suggested tests to add (minimal, use existing test framework pytest):
- `tests/test_build_knowledge_base_modes.py` — extend with new calls and asserts
	for returned `ChromaDBStatus` and whether the collection count changed when
	`add_documents` is True vs False.

Edge cases & guidance for the coding agent
-----------------------------------------
- Avoid destructive defaults: do not delete or overwrite an existing
	persistent DB unless an explicit `overwrite=True` flag is requested.
- If `chromaDB_path` is None and `create_new` is False, prefer to read the
	default path from `config['vector_db']['chromaDB_path']`. If that is also
	missing, raise a clear ValueError instead of silently creating in-memory.
- Keep logging informative — indicate requested intent vs actual result.
- Keep code changes minimal: add parameters, small branches, pass the flags
	along. Do not rewrite text splitting or embedding logic.

What to commit
--------------
- Edit `rag_kmk/knowledge_base/document_loader.py` (small changes to signature
	and logic). Keep unit tests green.
- Edit `rag_kmk/vector_db/database.py` to accept `create_new` and return
	clearer status. Keep changes minimal.
- Edit `run.py` to include updated example usage (comments only).
- Add/update `tests/test_build_knowledge_base_modes.py` or the relevant test
	file with a couple of small asserts.

If anything is unclear, prefer conservative, non-destructive behavior and
document the assumptions in code comments.

End of prompt

