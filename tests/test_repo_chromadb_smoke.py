import pytest
from pathlib import Path


def _chroma_present():
    return Path('chromaDB').exists()


@pytest.mark.skipif(not _chroma_present(), reason="no local chromaDB folder to test against")
def test_load_repo_chromadb():
    """Smoke test: load the persistent chromaDB directory in repo root and
    ensure it can be opened without raising an exception. This doesn't assert
    on counts because different stored DB formats may vary.
    """
    from rag_kmk.knowledge_base import build_knowledge_base

    kb, status = build_knowledge_base(document_directory_path=None, chromaDB_path=str(Path('chromaDB').resolve()))
    assert kb is not None
    assert status is not None
