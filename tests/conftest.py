import os
import sys
import pytest
import warnings
from types import SimpleNamespace

# Suppress deprecation warnings from PyMuPDF (fitz) SWIG bindings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="fitz")

# Make package importable when running tests from tests/ directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import rag_kmk
from rag_kmk import CONFIG


@pytest.fixture(scope='session')
def sample_docs_dir():
    return os.path.join(os.path.dirname(__file__), 'sample_documents')


@pytest.fixture
def tmp_chroma_dir(tmp_path, monkeypatch):
    path = tmp_path / "chromaDB"
    path.mkdir()
    # Override config for tests that read from CONFIG
    monkeypatch.setitem(CONFIG, 'vector_db', CONFIG.get('vector_db', {}))
    CONFIG['vector_db']['chromaDB_path'] = str(path)
    yield str(path)


@pytest.fixture
def mock_chroma_client(monkeypatch):
    # Provide a minimal fake collection object and inject a fake `chromadb`
    # module into sys.modules. This mocks the third-party dependency rather
    # than the internal rag_kmk API.
    import types as _types

    fake_collection = SimpleNamespace()
    fake_collection._items = []
    fake_collection.count = lambda: len(fake_collection._items)

    def add(ids, metadatas, documents, collection=None):
        fake_collection._items.extend(documents)
        return fake_collection

    fake_collection.add = add
    fake_collection.get = lambda ids: {'metadatas': [{'document': 'sample.txt'}]}

    class FakeClient:
        def create_collection(self, name, embedding_function=None):
            fake_collection.name = name or 'rag_collection'
            return fake_collection

        def get_or_create_collection(self, name, embedding_function=None):
            return self.create_collection(name, embedding_function)

    class FakePersistentClient(FakeClient):
        def __init__(self, path=None):
            self.path = path

        def get_collection(self, name, embedding_function=None):
            fake_collection.name = name or 'rag_collection'
            return fake_collection

        def create_collection(self, name, embedding_function=None):
            fake_collection.name = name or 'rag_collection'
            return fake_collection

    chromadb_mod = _types.ModuleType('chromadb')
    chromadb_mod.Client = FakeClient
    chromadb_mod.PersistentClient = FakePersistentClient

    utils_mod = _types.ModuleType('chromadb.utils')
    utils_mod.embedding_functions = SimpleNamespace(
        SentenceTransformerEmbeddingFunction=lambda model_name, device='cpu': None
    )

    monkeypatch.setitem(sys.modules, 'chromadb', chromadb_mod)
    monkeypatch.setitem(sys.modules, 'chromadb.utils', utils_mod)

    # Return the fake collection for tests that want to inspect it
    return fake_collection
