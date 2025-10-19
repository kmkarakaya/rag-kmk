# ...run from repository root: c:\Codes\rag-kmk

# 1) See what changed
git status --porcelain=v1

# 2) If you want to restore only the files modified by our edits, list them:
# (adjust if you had other local uncommitted work you want to keep)
git restore --source=HEAD -- \
	rag_kmk/rag_client.py \
	rag_kmk/__init__.py \
	run.py \
	rag_kmk/knowledge_base/document_loader.py \
	rag_kmk/knowledge_base/text_splitter.py \
	rag_kmk/vector_db/database.py \
	README.md \
	.github/prompts/terminal.prompt.md

# 3) If you want to discard ALL local changes and untracked files and exactly match HEAD:
git restore .            # restore tracked files
git clean -fd            # remove untracked files and directories

# 4) If you want to reset to the remote branch (force match origin/main):
git fetch origin
git reset --hard origin/main

# 5) Verify clean state and run the sample
git status
python run.py

# If you do NOT use git or have no commits to restore from, let me know and I will
# prepare minimal, careful edits to revert the specific files back to a safe state.
