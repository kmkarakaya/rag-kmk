import os
import pytest

from pathlib import Path
import types


def _import_chroma():
    try:
        import chromadb  # type: ignore
        return True
    except Exception:
        return False


def _sample_docs_path():
    p = Path(__file__).parent.parent / "tests" / "sample_documents"
    return p if p.exists() else None


def _repo_root():
    return Path(__file__).resolve().parents[2]


@pytest.mark.skipif(not _import_chroma(), reason="chromadb not installed")
def test_mode1_persistent_plus_add(tmp_path, monkeypatch):
    """
    Mode 1: load existing chromadb collection and add new documents.
    We simulate a persistent chroma DB by creating a directory under tmp_path
    and passing it as chromaDB_path. The function should return a collection
    and a status indicating persistent (existing or new persistent).
    """
    sample = _sample_docs_path()
    if sample is None:
        pytest.skip("sample documents not present in tests/sample_documents")

    # create a fake persistent directory
    persistent_dir = tmp_path / "chromaDB_persistent"
    persistent_dir.mkdir()

    from rag_kmk.knowledge_base import build_knowledge_base
    from rag_kmk.knowledge_base.document_loader import load_knowledge_base
    from rag_kmk.vector_db.database import ChromaDBStatus
    # Create (or open) a persistent collection and ingest documents
    kb, status = build_knowledge_base(collection_name='test_coll_mode1', document_directory_path=str(sample), add_documents=True, chromaDB_path=str(persistent_dir))

    assert kb is not None
    # Accept several success-like statuses; ensure not ERROR
    assert status != ChromaDBStatus.ERROR

    # The collection should contain documents after adding sample documents
    assert hasattr(kb, 'count'), "Returned collection object must implement count()"
    assert kb.count() > 0, "Persistent collection should contain documents after adding sample documents"


@pytest.mark.skipif(not _import_chroma(), reason="chromadb not installed")
def test_mode2_persistent_only(tmp_path):
    """
    Mode 2: load existing chromadb collection without adding new documents.
    We simulate an existing persistent collection by first creating one with
    a document, then loading it again without adding new documents.
    """
    sample = _sample_docs_path()
    if sample is None:
        pytest.skip("sample documents not present in tests/sample_documents")

    # create a fake persistent directory
    persistent_dir = tmp_path / "chromaDB_persistent2"
    persistent_dir.mkdir()

    from rag_kmk.knowledge_base import build_knowledge_base
    from rag_kmk.knowledge_base.document_loader import load_knowledge_base
    from rag_kmk.vector_db.database import ChromaDBStatus

    # 1. Create and populate the persistent DB
    kb_initial, status_initial = build_knowledge_base(collection_name='test_coll_mode2', document_directory_path=str(sample), add_documents=True, chromaDB_path=str(persistent_dir))
    assert kb_initial is not None
    assert kb_initial.count() > 0
    initial_count = kb_initial.count()

    # 2. Load the existing collection without adding new documents
    kb, status = load_knowledge_base(collection_name='test_coll_mode2', cfg={'vector_db': {'chromaDB_path': str(persistent_dir)}})

    assert kb is not None
    # This time it must be an existing permanent collection
    assert status == ChromaDBStatus.EXISTING_PERMANENT

    # The count should be the same as before, proving no new docs were added
    # and existing ones were loaded.
    assert hasattr(kb, 'count'), "Returned collection object must implement count()"
    assert kb.count() == initial_count


@pytest.mark.skipif(not _import_chroma(), reason="chromadb not installed")
def test_mode3_ephemeral_persistent_plus_add(monkeypatch):
    """
    Mode 3: create a new ephemeral persistent chromadb collection and add new documents to it.
    Use a temporary directory for the persistent store and verify ingestion.
    """
    sample = _sample_docs_path()
    if sample is None:
        pytest.skip("sample documents not present in tests/sample_documents")

    # The library no longer supports implicit in-memory mode. Create a
    # temporary persistent directory and use it for an ephemeral collection.
    from rag_kmk.vector_db.database import create_chroma_client, ChromaDBStatus
    from rag_kmk.knowledge_base import load_and_add_documents
    import tempfile

    td = tempfile.mkdtemp()
    client = None
    try:
        client, collection, status = create_chroma_client(chromaDB_path=td, collection_name='test_coll_mode3')
        # Expect persistent creation to succeed
        assert status in (ChromaDBStatus.NEW_PERSISTENT_CREATED, ChromaDBStatus.OK)
        files_processed, errors = load_and_add_documents(collection, str(sample), {})
        assert files_processed is True
        assert collection.count() > 0
        # Best-effort: persist and close the client to release file handles
        try:
            if client is not None and hasattr(client, 'persist'):
                client.persist()
        except Exception:
            pass
        try:
            if client is not None and hasattr(client, 'close'):
                client.close()
        except Exception:
            pass
    finally:
        # Attempt robust cleanup on Windows: retry rmtree a few times to account for delayed file handle release
        import shutil, time
        for attempt in range(6):
            try:
                shutil.rmtree(td)
                break
            except PermissionError:
                time.sleep(0.2)
        else:
            # Last resort: ignore cleanup failure (temp dir will remain)
            pass


@pytest.mark.skipif(not _import_chroma(), reason="chromadb not installed")
def test_load_and_add_documents_public_api(tmp_path):
    """
    Test the public `load_and_add_documents` function directly.
    It should take an existing collection and add documents to it.
    """
    from rag_kmk.knowledge_base import load_and_add_documents
    from rag_kmk.vector_db.database import create_chroma_client
    from rag_kmk import CONFIG

    # 1. Create an empty temporary persistent collection to pass to the function
    persistent_dir = tmp_path / "chromaDB_tmp"
    persistent_dir.mkdir()
    client, collection, _ = create_chroma_client(
        chromaDB_path=str(persistent_dir),
        collection_name=f"test_collection_{tmp_path.name}"
    )
    assert collection is not None
    assert collection.count() == 0

    # 2. Create a temporary directory with a sample document
    sample_dir = tmp_path / "docs"
    sample_dir.mkdir()
    (sample_dir / "test.txt").write_text("This is a test document.")

    # 3. Call the function to load documents into the collection
    files_processed, errors = load_and_add_documents(
        collection, str(sample_dir), CONFIG
    )

    # 4. Assert that documents were added
    assert files_processed is True
    assert not errors
    assert collection.count() > 0
