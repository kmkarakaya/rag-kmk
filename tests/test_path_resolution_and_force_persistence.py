import pytest

from rag_kmk.knowledge_base import document_loader as dl_mod
from rag_kmk.vector_db.database import ChromaDBStatus


def make_stub_collector(captured: dict, return_status=ChromaDBStatus.EXISTING_PERSISTENT):
    """Return a stub for vdb_database.create_chroma_client that captures its args."""

    def stub_create_chroma_client(collection_name=None, chromaDB_path=None, create_new=False, config=None):
        captured['collection_name'] = collection_name
        captured['chromaDB_path'] = chromaDB_path
        captured['create_new'] = create_new
        captured['config'] = config
        # return a fake collection object and a status
        return object(), return_status

    return stub_create_chroma_client


def test_explicit_path_used(monkeypatch):
    captured = {}
    stub = make_stub_collector(captured, return_status=ChromaDBStatus.EXISTING_PERSISTENT)
    monkeypatch.setattr(dl_mod, 'load_config', lambda: {})
    monkeypatch.setattr(dl_mod.vdb_database, 'create_chroma_client', stub)

    # Provide an explicit chromaDB_path
    collection, status = dl_mod.build_knowledge_base(document_directory_path=None, chromaDB_path='./explicitDB', create_new=False, add_documents=False)

    assert status == ChromaDBStatus.EXISTING_PERSISTENT
    assert captured['chromaDB_path'] == './explicitDB'


def test_config_default_used_when_omitted(monkeypatch):
    captured = {}
    stub = make_stub_collector(captured, return_status=ChromaDBStatus.EXISTING_PERSISTENT)
    # Provide a config with a default chromaDB_path
    monkeypatch.setattr(dl_mod, 'load_config', lambda: {'vector_db': {'chromaDB_path': './configDB', 'collection_name': 'cfg_col'}})
    monkeypatch.setattr(dl_mod.vdb_database, 'create_chroma_client', stub)

    # Omit chromaDB_path so it should fall back to config
    collection, status = dl_mod.build_knowledge_base(document_directory_path=None, create_new=False, add_documents=False)

    assert status == ChromaDBStatus.EXISTING_PERSISTENT
    assert captured['chromaDB_path'] == './configDB'


def test_explicit_none_requests_inmemory(monkeypatch):
    captured = {}
    stub = make_stub_collector(captured, return_status=ChromaDBStatus.NEW_MEMORY)
    monkeypatch.setattr(dl_mod, 'load_config', lambda: {'vector_db': {'chromaDB_path': './configDB'}})
    monkeypatch.setattr(dl_mod.vdb_database, 'create_chroma_client', stub)

    # Explicit chromaDB_path=None with create_new=True requests in-memory
    collection, status = dl_mod.build_knowledge_base(document_directory_path='docs', chromaDB_path=None, create_new=True, add_documents=False)

    assert status == ChromaDBStatus.NEW_MEMORY
    assert captured['chromaDB_path'] is None


def test_force_persistence_false_overrides_config(monkeypatch):
    captured = {}
    stub = make_stub_collector(captured, return_status=ChromaDBStatus.NEW_MEMORY)
    # Config provides a persistent path but force_persistence=False should force in-memory
    monkeypatch.setattr(dl_mod, 'load_config', lambda: {'vector_db': {'chromaDB_path': './configDB'}})
    monkeypatch.setattr(dl_mod.vdb_database, 'create_chroma_client', stub)

    collection, status = dl_mod.build_knowledge_base(document_directory_path='docs', create_new=True, add_documents=False, force_persistence=False)

    assert status == ChromaDBStatus.NEW_MEMORY
    assert captured['chromaDB_path'] is None


def test_force_persistence_true_requires_path(monkeypatch):
    # If neither arg nor config provide a path, force_persistence=True should raise
    monkeypatch.setattr(dl_mod, 'load_config', lambda: {})

    with pytest.raises(ValueError):
        dl_mod.build_knowledge_base(document_directory_path=None, create_new=True, add_documents=False, force_persistence=True)


def test_explicit_none_without_create_new_is_error(monkeypatch):
    # Explicit chromaDB_path=None with create_new=False should raise ValueError
    monkeypatch.setattr(dl_mod, 'load_config', lambda: {'vector_db': {'chromaDB_path': './configDB'}})

    with pytest.raises(ValueError):
        dl_mod.build_knowledge_base(document_directory_path=None, chromaDB_path=None, create_new=False, add_documents=False)
