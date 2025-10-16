import os
from pathlib import Path

from rag_kmk.knowledge_base.document_loader import build_knowledge_base


def test_build_knowledge_base_with_mock(mock_chroma_client, tmp_path):
    # create a tiny text file
    docs = tmp_path / 'docs'
    docs.mkdir()
    f = docs / 'sample.txt'
    f.write_text('Hello world. This is a test document.')

    collection, status = build_knowledge_base(collection_name='test_mock', document_directory_path=str(docs), add_documents=True, chromaDB_path=None)

    # With the mocked create_chroma_client, build_knowledge_base returns the fake collection and status
    assert status is not None
    # collection should expose count() method (mocked)
    assert hasattr(collection, 'count')


import os
import json
import tempfile
from rag_kmk.knowledge_base import document_loader as dl
from rag_kmk.vector_db import database as vdb_database


def _fake_create_chroma_client(collection_name, chromaDB_path, create_new=False, config=None):
    """
    Simple fake factory that ensures the chromaDB_path exists when create_new=True
    and returns a FakeCollection with count/get methods.
    """

    class FakeCollection:
        def __init__(self, name):
            self.name = name

        def count(self, *args, **kwargs):
            return 0

        def get(self, include=None):
            return {"ids": []}

    # create folder when requested
    if create_new:
        os.makedirs(chromaDB_path, exist_ok=True)
        return None, FakeCollection(collection_name), vdb_database.ChromaDBStatus.NEW_PERSISTENT_CREATED
    else:
        # require folder exists and non-empty (the caller may create marker file)
        if not os.path.isdir(chromaDB_path) or not os.listdir(chromaDB_path):
            return None, None, vdb_database.ChromaDBStatus.MISSING_PERSISTENT
        # simulate missing collection if folder present but collection absent is not detected here
        return None, FakeCollection(collection_name), vdb_database.ChromaDBStatus.OK


def test_build_knowledge_base_create_and_ingest(tmp_path, monkeypatch):
    # prepare a small doc folder with one txt file
    doc_dir = tmp_path / "docs"
    doc_dir.mkdir()
    doc_file = doc_dir / "sample.txt"
    doc_file.write_text("This is a small test document.\nIt has multiple lines.")

    # prepare a chroma persistent folder path inside tmp
    persist_dir = tmp_path / "chroma_persist"
    # cfg instructs loader to use this chroma path
    cfg = {
        "vector_db": {"chromaDB_path": str(persist_dir)},
        "supported_file_types": [".txt"],
        "tokens_per_chunk": 64,
    }

    # monkeypatch the DB factory and the add_document_to_collection to be a noop
    monkeypatch.setattr(vdb_database, "create_chroma_client", _fake_create_chroma_client)
    # stub out add_document_to_collection to avoid depending on real chroma client API
    monkeypatch.setattr(dl, "add_document_to_collection", lambda ids, metas, chunks, collection: None)

    # call build_knowledge_base to create DB and ingest
    collection_name = "test_coll"
    kb, status = dl.build_knowledge_base(
        collection_name=collection_name,
        document_directory_path=str(doc_dir),
        add_documents=True,
        cfg=cfg
    )

    assert status in (vdb_database.ChromaDBStatus.NEW_PERSISTENT_CREATED, vdb_database.ChromaDBStatus.OK)
    assert kb is not None


def test_build_knowledge_base_open_existing(tmp_path, monkeypatch):
    # create persistent dir with a marker so factory doesn't treat as missing
    persist_dir = tmp_path / "chroma_persist_open"
    persist_dir.mkdir()
    (persist_dir / "marker.txt").write_text("x")

    cfg = {"vector_db": {"chromaDB_path": str(persist_dir)}, "supported_file_types": [".txt"], "tokens_per_chunk": 64}

    monkeypatch.setattr(vdb_database, "create_chroma_client", _fake_create_chroma_client)
    monkeypatch.setattr(dl, "add_document_to_collection", lambda ids, metas, chunks, collection: None)

    # Use load_knowledge_base for open-only semantics
    from rag_kmk.knowledge_base.document_loader import load_knowledge_base
    kb, status = load_knowledge_base(collection_name="test_coll", cfg=cfg)

    assert status == vdb_database.ChromaDBStatus.OK
    assert kb is not None
