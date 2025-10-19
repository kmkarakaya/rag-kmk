import os
import types
import pytest
from pathlib import Path

from rag_kmk.knowledge_base import document_loader as dl
from rag_kmk.vector_db import database as vdb_database


def make_fake_collection_with_count(value):
    class C:
        def count(self, *args, **kwargs):
            return value

        def get(self, include=None):
            return {"ids": []}

    return C()


def test_resolve_collection_count_various_shapes():
    # count() -> int
    c1 = make_fake_collection_with_count(5)
    assert dl._resolve_collection_count(c1) == 5

    # count() -> dict
    class Cdict:
        def count(self, *a, **k):
            return {"count": 3}

    assert dl._resolve_collection_count(Cdict()) == 3

    # count() raises TypeError, but get() returns ids
    class Cget:
        def count(self, *a, **k):
            raise TypeError()

        def get(self, include=None):
            return {"ids": [1, 2, 3, 4]}

    assert dl._resolve_collection_count(Cget()) == 4

    # get() returns list
    class Clist:
        def count(self, *a, **k):
            raise Exception()

        def get(self, include=None):
            return [1, 2]

    assert dl._resolve_collection_count(Clist()) == 2


def test_load_knowledge_base_missing_cfg_path(tmp_path, monkeypatch):
    # cfg missing vector_db.chromaDB_path should yield ERROR
    kb, status = dl.load_knowledge_base(collection_name="x", cfg={})
    assert status == vdb_database.ChromaDBStatus.ERROR
    assert kb is None


def test_load_knowledge_base_missing_persistent(tmp_path, monkeypatch):
    # Provide a cfg that references a non-existent directory
    cfg = {"vector_db": {"chromaDB_path": str(tmp_path / 'nope_dir')}}
    kb, status = dl.load_knowledge_base(collection_name="x", cfg=cfg)
    assert status == vdb_database.ChromaDBStatus.MISSING_PERSISTENT
    assert kb is None


def test_load_knowledge_base_factory_return_shapes(monkeypatch, tmp_path):
    # Create a real directory to satisfy path exists check
    d = tmp_path / 'persist'
    d.mkdir()
    cfg = {"vector_db": {"chromaDB_path": str(d)}}

    # Case A: factory returns (client, collection, status)
    class FakeColl:
        pass

    def fake_factory_a(collection_name, chromaDB_path, create_new=False, config=None):
        return object(), FakeColl(), vdb_database.ChromaDBStatus.OK

    monkeypatch.setattr(dl.vdb_database, 'create_chroma_client', fake_factory_a)
    kb, status = dl.load_knowledge_base(collection_name='c', cfg=cfg)
    assert status == vdb_database.ChromaDBStatus.OK
    assert isinstance(kb, FakeColl)

    # Case B: factory returns (collection, status)
    def fake_factory_b(collection_name, chromaDB_path, create_new=False, config=None):
        return FakeColl(), vdb_database.ChromaDBStatus.OK

    monkeypatch.setattr(dl.vdb_database, 'create_chroma_client', fake_factory_b)
    kb, status = dl.load_knowledge_base(collection_name='c', cfg=cfg)
    assert status == vdb_database.ChromaDBStatus.OK
    assert isinstance(kb, FakeColl)


def test_build_knowledge_base_already_exists(monkeypatch, tmp_path):
    # Simulate ALREADY_EXISTS from factory
    d = tmp_path / 'persist'
    d.mkdir()

    def fake_factory(collection_name, chromaDB_path, create_new=True, config=None):
        return None, None, vdb_database.ChromaDBStatus.ALREADY_EXISTS

    monkeypatch.setattr(dl.vdb_database, 'create_chroma_client', fake_factory)
    kb, status = dl.build_knowledge_base(collection_name='c', document_directory_path=None, add_documents=False, chromaDB_path=str(d))
    assert status == vdb_database.ChromaDBStatus.ALREADY_EXISTS
    assert kb is None


def test_build_knowledge_base_add_documents_missing_path(monkeypatch):
    kb, status = dl.build_knowledge_base(collection_name='c', document_directory_path=None, add_documents=True, chromaDB_path=None)
    assert status == vdb_database.ChromaDBStatus.ERROR
    assert kb is None


def test_load_and_add_documents_txt_and_skip_unsupported(tmp_path, monkeypatch):
    # prepare directory with txt and unsupported extension
    docs = tmp_path / 'docs'
    docs.mkdir()
    (docs / 'a.txt').write_text('hello')
    (docs / 'b.bin').write_text('bin')

    class FakeCollection:
        def __init__(self):
            self._ids = []

        def count(self, *a, **k):
            return len(self._ids)

        def get(self, include=None):
            return {"ids": self._ids}

    fake = FakeCollection()

    # monkeypatch add_document_to_collection to append ids
    def fake_add(ids, metas, chunks, collection):
        fake._ids.extend(ids)

    monkeypatch.setattr(dl, 'add_document_to_collection', fake_add)

    files_processed, errors = dl.load_and_add_documents(fake, str(docs), {})
    assert files_processed is True
    assert not errors
    assert fake.count() > 0


def test_load_and_add_documents_docx_missing_docx2txt(tmp_path, monkeypatch):
    docs = tmp_path / 'docs'
    docs.mkdir()
    # create a .docx file (just a text file suffices for our handling)
    (docs / 'a.docx').write_text('docx content')

    # Ensure docx2txt import raises ImportError
    monkeypatch.setitem(__import__('sys').modules, 'docx2txt', None)

    class FakeCollection:
        def count(self, *a, **k):
            return 0

    fake = FakeCollection()

    files_processed, errors = dl.load_and_add_documents(fake, str(docs), {})
    # Since docx2txt missing, expect errors mentioning docx2txt
    assert not files_processed
    assert any('docx2txt' in e for e in errors)


def test_load_and_add_documents_client_persist_nonfatal(tmp_path, monkeypatch):
    docs = tmp_path / 'docs'
    docs.mkdir()
    (docs / 'a.txt').write_text('hello')

    class FakeCollection:
        def __init__(self):
            self._ids = []

        def count(self, *a, **k):
            return len(self._ids)

        def get(self, include=None):
            return {"ids": self._ids}

    fake = FakeCollection()

    def fake_add(ids, metas, chunks, collection):
        fake._ids.extend(ids)

    monkeypatch.setattr(dl, 'add_document_to_collection', fake_add)

    class BadClient:
        def persist(self):
            raise RuntimeError('fail persist')

    monkeypatch.setattr(dl.vdb_database, 'get_client_for_collection', lambda c: BadClient())

    files_processed, errors = dl.load_and_add_documents(fake, str(docs), {})
    assert files_processed is True
    assert not errors
