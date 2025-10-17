from rag_kmk.vector_db.database import create_chroma_client, ChromaDBStatus


def test_create_chroma_client_no_inmemory():
    # Request without a persistent path (None) should not create an in-memory client
    client, collection, status = create_chroma_client(chromaDB_path=None)
    # The factory no longer supports implicit in-memory clients. Expect a missing persistent path or error.
    assert status in (ChromaDBStatus.MISSING_PERSISTENT, ChromaDBStatus.ERROR)
    # Ensure that for missing persistent path, client/collection are not returned
    if status == ChromaDBStatus.MISSING_PERSISTENT:
        assert client is None and collection is None
    else:
        # On ERROR it's acceptable for client/collection to be None
        assert client is None or collection is None
