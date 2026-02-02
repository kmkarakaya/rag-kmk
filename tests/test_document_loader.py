import os
from pathlib import Path

from rag_kmk.knowledge_base.document_loader import load_and_add_documents
from rag_kmk import CONFIG


def test_build_knowledge_base_create_and_ingest_real(tmp_path, monkeypatch):
    # create a tiny text file
    docs = tmp_path / 'docs'
    docs.mkdir()
    f = docs / 'sample.txt'
    f.write_text('Hello world. This is a test document.')

    # Use a temp chroma persistent path via CONFIG
    persist_dir = tmp_path / 'chroma'
    cfg = {
        'vector_db': {'chromaDB_path': str(persist_dir)},
        'supported_file_types': ['.txt'],
        'knowledge_base': {'tokens_per_chunk': 128},
        'llm': {},
    }

    # Create a chroma client/collection using runtime vector db factory
    from rag_kmk.vector_db import database as vdb_database
    client, collection, status = vdb_database.create_chroma_client(collection_name='test_real', chromaDB_path=str(persist_dir), create_new=True, config=cfg.get('vector_db'))
    # Now ingest documents using the loader
    processed, errors = load_and_add_documents(collection, str(docs), cfg)
    assert processed is True
    assert errors == []


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


def test_build_knowledge_base_open_existing_real(tmp_path):
    # create persistent dir with a marker so factory doesn't treat as missing
    persist_dir = tmp_path / "chroma_persist_open"
    persist_dir.mkdir()
    (persist_dir / "marker.txt").write_text("x")

    cfg = {"vector_db": {"chromaDB_path": str(persist_dir)}, "supported_file_types": [".txt"], "knowledge_base": {"tokens_per_chunk": 64}}

    # Try to open by creating a client without create_new to simulate existing directory
    from rag_kmk.vector_db import database as vdb_database
    client, collection, status = vdb_database.create_chroma_client(collection_name='test_coll', chromaDB_path=str(persist_dir), create_new=False, config=cfg.get('vector_db'))
    # The collection may be missing, but the call should return statuses without throwing
    assert status is not None
