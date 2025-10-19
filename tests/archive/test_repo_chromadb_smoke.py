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
    from rag_kmk.knowledge_base.document_loader import load_knowledge_base

    kb, status = load_knowledge_base(collection_name='default', cfg={'vector_db': {'chromaDB_path': str(Path('chromaDB').resolve())}})

    # Opening may fail if formats differ; ensure we get a non-ERROR status and no exception raised
    # Ensure we got a non-ERROR status (compare by name to avoid import-time package attribute issues)
    assert status is not None
    assert getattr(status, 'name', None) != 'ERROR'
