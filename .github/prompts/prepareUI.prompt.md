Prepare UI prompt for an MVP NotebookLM-like single-file UI (`notebookLM.py`)
==============================================================


Summary / priority
------------------

We need a very small, single-file MVP that looks and feels like a minimal NotebookLM: chat-first UX that lets a user create or open a knowledge base (Chroma collection), inspect it, and ask questions. The highest priority is brevity and a clear chat-centric flow that uses the same library functions showcased in `run.py` (create+ingest via `build_knowledge_base`, open-only via `load_knowledge_base`, `summarize_collection`, and the `chat_flow` pipeline). All functionality must live in `notebookLM.py`.

Top-level requirements (MVP)
----------------------------

- Single Python file: `notebookLM.py` implementing the whole app (server, HTML, JS).
- Minimal dependencies: prefer Flask (serve UI) and vanilla JS. Playwright is optional for an `--open` convenience flag.
- Bind only to localhost (127.0.0.1). No authentication.
- Use `rag_kmk` public APIs only. Do not change library code.

User-facing MVP features (in order of priority)
-----------------------------------------------

1. Chat-first experience: a chat box where the user types a query and receives an answer that is augmented by retrieved documents from a selected collection.
2. Create + ingest a collection from a local folder (single form). This uses `document_loader.build_knowledge_base(collection_name, document_directory_path, add_documents=True)` and reports status.
3. Load an existing collection (open-only) using `document_loader.load_knowledge_base(collection_name, cfg=...)`.
4. List and select session collections; show a summary via `summarize_collection(collection)` when selected.
5. Basic logs and status messages displayed in the UI (ingest success/errors, load errors, LLM errors).

Minimal technical contract (endpoints & behavior)
-------------------------------------------------

- Single-page app served by Flask with these JSON endpoints:
  - GET / -> HTML UI
  - GET /api/collections -> session collections + selected
  - POST /api/create -> {collection_name, document_directory_path} -> create+ingest via build_knowledge_base
  - POST /api/load -> {collection_name} -> open-only via load_knowledge_base
  - POST /api/select -> {collection_name} -> mark selection
  - POST /api/summarize -> {collection_name} -> calls summarize_collection and returns JSON summary
  - POST /api/chat -> {collection_name, query} -> run a single-query RAG chat
  - POST /api/unload -> remove from session list

Chat endpoint details (simplified)
----------------------------------

- Preferred: call `chat_flow.build_chatBot(CONFIG.get('llm', {}))` to obtain a client and then call `chat_flow.run_rag_pipeline(client, collection)` if the pipeline supports single-query programmatic invocation in the repo; if that function runs an interactive loop, instead perform a conservative flow:
  1. Retrieve relevant chunks via the collection or the repo's query helpers (minimal retrieval step) — or call a simple wrapper that the repo exposes.
  2. Call the LLM client (via `build_chatBot`) with a composed prompt using retrieved context.
- Return the textual answer to the UI. Close client if it exposes close().

UI & UX details (very small)
----------------------------

- Layout: header, left panel (create/load controls and collection list), right panel (chat + summary + logs).
- Chat history shows user and assistant messages. Input box + send button.
- Create form: collection name + folder path text input + "Create & Ingest" button.
- Load form: collection name + "Load" button.
- Show small badges for collection status (OK, MISSING_PERSISTENT, ALREADY_EXISTS, ERROR).

Error handling & user messages
------------------------------

- Validate collection name is non-empty. For create: validate that the folder exists before calling ingest.
- Display `ChromaDBStatus` names in the UI for clarity.
- For ingestion errors, present the returned errors from `load_and_add_documents` (if available) and do not register the collection in session state.

Developer notes & acceptance criteria
-------------------------------------

Acceptance (MVP):

1. `python notebookLM.py` starts a local server (e.g., http://127.0.0.1:5005) and serves the UI.
2. Using the Create form with `tests/sample_documents` creates and ingests a collection (collection appears in the list and summary is viewable).
3. The Load form can open an existing collection (when repo config points to a persistent chromaDB path) and it appears in the list.
4. Selecting a collection shows a summary and enables chat against it.
5. Chat returns text responses or an informative error if LLM isn't configured.

Testing notes
-------------

- Run in the `rag` conda environment used for tests.
- Ensure Flask is installed: `pip install flask`.
- Optional: `pip install playwright` and `playwright install` to support `--open` auto-launch.

Playwright MCP automated smoke-check (required when available)
--------------------------------------------------------------

- The coding agent should attempt an automated UI/UX smoke-check using the repository's MCP Playwright interface if Playwright is installed. This is a short end-to-end script (30–60s) that validates the primary flows.
- Smoke-check steps (high level):
  1. Start `notebookLM.py` server (127.0.0.1:5005).
  2. Navigate to the UI and perform the Create flow: fill collection name and `tests/sample_documents` as the folder, click "Create & Ingest".
  3. Wait until the collection appears in the session list and a success badge/status is shown.
  4. Select the collection, view summary, then send a chat query and assert an assistant response appears.
  5. The script should report pass/fail and exit cleanly. If Playwright is not available, print the UI URL and skip this check.

Security & scope
----------------

- Localhost only (127.0.0.1). No auth. Not production-ready.
- The file is strictly a demo/MVP and should not modify library code.
- IMPORTANT: The coding agent must only modify the single file `notebookLM.py` in the repository root. No other files in the repository may be changed. Any edits outside of `notebookLM.py` will be considered a failure to meet the task requirements.

# Additional mandatory rules for the coding agent (NEW)

- The repository's rag-kmk package already implements the full backend needed by the UI. The coding agent must treat rag-kmk as the backend and must NOT modify any library/backend files.
- The coding agent is allowed to modify exactly one file: notebookLM.py (located at the repository root). No other files may be created, modified, or deleted. Any edits outside notebookLM.py will be considered a failure.
- The coding agent must use run.py as the canonical example of how to call rag-kmk public APIs (build_knowledge_base, load_knowledge_base, summarize_collection, chat_flow helpers). Do not implement or mock backend behavior — call the library as-is.
- Do not add tests or helper modules. Do not write mock code for rag-kmk.
- Enforce localhost-only binding (127.0.0.1). No authentication requirements.

If this updated prompt looks good, implement `notebookLM.py` as a single-file Flask app following this minimal NotebookLM-like contract and test with the `tests/sample_documents` flow.

Note: When implementing, update only `notebookLM.py`. Keep all other repository files (including tests, docs, and configs) exactly as they are.
