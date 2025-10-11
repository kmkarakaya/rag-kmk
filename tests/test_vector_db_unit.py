from rag_kmk.vector_db.database import create_chroma_client, ChromaDBStatus


def test_create_chroma_client_in_memory():
    # Request an in-memory client by passing chromaDB_path=None
    client, collection, status = create_chroma_client(chromaDB_path=None)
    # The implementation can either create an in-memory collection or fail and return a FAILED_MEMORY status.
    assert status in (ChromaDBStatus.NEW_MEMORY, ChromaDBStatus.FAILED_MEMORY)
    if status == ChromaDBStatus.NEW_MEMORY:
        assert client is not None
        assert collection is not None
        # collection should have a count method
        assert hasattr(collection, 'count')
    else:
        # FAILED_MEMORY -> ensure the function returned None for client/collection
        assert client is None or collection is None
