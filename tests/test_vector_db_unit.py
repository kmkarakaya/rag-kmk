from rag_kmk.vector_db.database import create_chroma_client, ChromaDBStatus


def test_create_chroma_client_missing_path():
    # When no chromaDB path is provided, factory should indicate missing persistent
    client, collection, status = create_chroma_client(collection_name="col", chromaDB_path=None, create_new=False)
    assert status in (ChromaDBStatus.MISSING_PERSISTENT, ChromaDBStatus.ERROR)
