# Update README.md — Agent Prompt (improved, per-file systematic scan)

Prerequisite — required repository access (READ THIS FIRST)

- This task REQUIRES that you read the source files under: `c:\Codes\rag-kmk\rag_kmk` recursively before making any README changes.
- If you (the agent) have direct filesystem access to the repository, you MUST:
  1. Produce a deterministic listing of all files under `rag_kmk/` (sorted alphabetically) and confirm it in the first output step.
  2. Then read each file one-by-one in that sorted order, extracting public functions, classes, and configuration keys.
- If you do NOT have filesystem access, STOP and request one of the following from the human before proceeding:
  - A full listing of repository files: run in repo root `git ls-files` (paste output).
  - OR a zip/tarball of `rag_kmk/` source tree (attach or paste a download link).
  - OR the contents of specific files the agent cannot read (paste file contents). At minimum include:
    - rag_kmk/__init__.py
    - rag_kmk/config/config.py
    - rag_kmk/config/config.yaml (if present)
    - rag_kmk/knowledge_base/document_loader.py
    - rag_kmk/knowledge_base/text_splitter.py
    - rag_kmk/knowledge_base/*.py
    - rag_kmk/vector_db/database.py
    - rag_kmk/vector_db/query.py
    - rag_kmk/chat_flow/llm_interface.py
    - rag_kmk/utils.py
    - run.py
  - If none of the above is provided, DO NOT guess API signatures or change README. Request the missing artifacts.

Goal
Update README.md so it accurately reflects the current rag_kmk package state. The README must be concise, correct, and include minimal copy-paste examples that work with the current library code (do not execute code — only validate imports/signatures).

Systematic, per-file workflow (mandatory)

1. List files: produce a sorted list of all files under `rag_kmk/` and any other top-level modules relevant to README.
2. For each file in sorted order:
   a. Read file contents.
   b. Extract public API: top-level functions, classes, important constants, and configuration keys. Note signatures exactly as present in code.
   c. Immediately after extracting the public API for the current file, propose an incremental README edit (a minimal snippet or one-line change) that results from this file. Record the exact edit (target section, snippet, and rationale).
   d. Apply the incremental edit to an in-memory representation of `README.md` (do not write/commit yet). Continue to the next file only after the incremental edit is recorded in the verification report.
   e. Append a one-line summary of discoveries and any mismatches with the current README to the verification report, including any "To-do / Questions" if something is ambiguous.
3. After all files processed:
   - Merge the per-file proposals into a single coherent README.md (final edits only).
   - Produce `.github/prompts/updateReadME.report.txt` summarizing files scanned, key discoveries, mismatches, and outstanding questions.
   - Optionally append a 2–3 line changelog fragment under "What's new".

  Optional additions (ask the human before running these):

- Quick Start: run.py example — include a validated, <=30-line snippet using `initialize_rag()`, `build_chatBot()`, and `build_knowledge_base()` end-to-end. The agent MUST validate imports/signatures from the scanned files before adding the snippet to `README.md`.
- Optional extras / heavy-features list — document optional or heavy-feature dependencies required for ingestion and LLM support (examples: `chromadb`, `langchain`, `sentence-transformers`, `PyMuPDF`, `docx2txt`). The agent MUST follow this priority when generating README content:

  1. If `pyproject.toml` or `setup.cfg` declares install extras (e.g., `[project.optional-dependencies]` or `extras_require`), list the extras and suggest the `pip install rag-kmk[extra1,extra2]` form.
  2. Else if a repository-level `requirements.txt` exists and already lists the heavy packages, note in the README that installing from `requirements.txt` or installing the package will install those dependencies; do NOT duplicate full `pip install` lines unless the extras are truly optional at runtime.
  3. Otherwise, include explicit `pip install` lines for the suggested extras and mark them as optional ("for ingestion support, install ...").
     In all cases, keep the extras section short (2–5 lines) and factual: which features require which packages and whether they are installed by default.
- Testing step (opt-in) — the agent may run the test suite (`pytest -q tests`) only after explicit permission. If run, include a brief test summary (PASS/FAIL, failing test names) in the verification report. Warn the user about potential time requirements and ask for confirmation when the test run may be lengthy.

Validation rules

- Always include `rag_kmk/config/config.yaml` if present; extract config keys used by code.
- Include query.py and text_splitter.py signatures in API reference if they exist.
- Keep code examples <= 20 lines and use environment variable placeholders for secrets.
- Ensure all import paths in README snippets are valid (use the exact module paths discovered).
- If a signature or behavior is dynamic/constructed at runtime and cannot be determined statically, list it under "To-do / Questions" in the verification report — do NOT guess.
- Maintain the original README constraints: short sections, badges preserved, and avoid secrets.

Required README sections (minimum)

- Title & short description
- Quick Install (pip and from-source)
- Quick Start / Minimal Example (use run.py as canonical)
- Configuration (include keys from config.yaml and normalization behavior such as chroma_db -> chromaDB_path)
- API Reference (one-line descriptions with exact signatures discovered)
- Persistence & semantics (explicit precedence rules for chromaDB_path)
- Development & Testing (pytest and coverage)
- Contributing & CI (docs/contributing.md and .github/workflows)
- Troubleshooting & Notes (no-op ChatClient fallback, timeouts)
- Changelog fragment (2–3 lines)

Outputs to produce

- Updated README.md at repository root (edit in-place).
- Verification report: `.github/prompts/updateReadME.report.txt` listing:
  - Sorted files scanned
  - Per-file discoveries (one-line per exported item)
  - Mismatches and "To-do / Questions"
- Optionally: docs/CHANGELOG.md fragment or "What's new" section in README.

Failure modes / When to stop and ask for help

- Missing access to rag_kmk/ files — request git ls-files or archive.
- Ambiguous/dynamic signatures — list under "To-do / Questions" and stop.
- Conflicting information between run.py and module signatures — prefer module source; note contradictions in the report.

Style & formatting constraints

- Use standard Markdown; keep sections short and scannable.
- Put code examples in fenced code blocks and keep them minimal (<=20 lines).
- Do not include secrets; use environment variable placeholders.

End of improved prompt.
