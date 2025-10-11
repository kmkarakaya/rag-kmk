import os
import sys
import pytest
from types import SimpleNamespace

# Make package importable when running tests from tests/ directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import rag_kmk
from rag_kmk import CONFIG


@pytest.fixture(scope='session')
def sample_docs_dir():
    return os.path.join(os.path.dirname(__file__), 'sample_documents')


@pytest.fixture
def tmp_chroma_dir(tmp_path, monkeypatch):
    path = tmp_path / "chroma_db"
    path.mkdir()
    # Override config for tests that read from CONFIG
    monkeypatch.setitem(CONFIG, 'vector_db', CONFIG.get('vector_db', {}))
    CONFIG['vector_db']['chromaDB_path'] = str(path)
    yield str(path)


@pytest.fixture
def mock_chroma_client(monkeypatch):
    # Provide a minimal fake collection object
    fake_collection = SimpleNamespace()
    fake_collection._items = []
    fake_collection.count = lambda : len(fake_collection._items)

    def add(ids, metadatas, documents, collection):
        fake_collection._items.extend(documents)
        return fake_collection

    fake_collection.add = add
    fake_client = SimpleNamespace()
    status = SimpleNamespace(value='MOCK')

    def fake_create_chroma_client(chromaDB_path=None, collection_name=None, sentence_transformer_model=None):
        return fake_client, fake_collection, status

    monkeypatch.setattr('rag_kmk.vector_db.database.create_chroma_client', fake_create_chroma_client)
    return fake_create_chroma_client
