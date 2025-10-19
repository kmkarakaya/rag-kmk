import types
import importlib
import pytest
import sys


def make_fake_collection():
    class FakeCollection:
        def __init__(self, name='fake'):
            self.name = name

        def count(self, *a, **k):
            return 0

        def get(self, include=None):
            return {'ids': []}

    return FakeCollection()


@pytest.fixture(autouse=True)
def patch_vector_db(monkeypatch, tmp_path):
    # Provide a fake chroma client and collection
    fake_client = object()
    fake_collection = make_fake_collection()

    def fake_create_chromadb_client(path=None):
        return {'status': 'CLIENT_READY', 'client': fake_client, 'error': None}

    def fake_list_collection_names(client):
        return {'status': 'COLLECTION_LISTED', 'collections': [], 'error': None}

    def fake_load_collection(client, name):
        return ({'status': 'COLLECTION_LOADED', 'error': None}, fake_collection)

    monkeypatch.setattr('rag_kmk.vector_db.database.create_chromadb_client', fake_create_chromadb_client)
    monkeypatch.setattr('rag_kmk.vector_db.database.list_collection_names', fake_list_collection_names)
    monkeypatch.setattr('rag_kmk.vector_db.database.load_collection', fake_load_collection)

    # Also patch query.retrieve_chunks to return a small context list
    fake_query = types.SimpleNamespace()
    fake_query.retrieve_chunks = lambda col, prompt, n_results=5, return_only_docs=False: ['doc snippet 1', 'doc snippet 2'] if return_only_docs else []
    monkeypatch.setitem(sys.modules, 'rag_kmk.vector_db.query', fake_query)

    yield


def test_rag_client_chat_smoke(monkeypatch):
    # Patch LLM builder and generation to avoid external calls
    llm_mod = types.SimpleNamespace()
    llm_mod.build_chatBot = lambda cfg: object()
    llm_mod.generate_LLM_answer = lambda client, prompt, timeout_seconds=30: 'fake answer'
    monkeypatch.setitem(__import__('sys').modules, 'rag_kmk.chat_flow.llm_interface', llm_mod)

    from rag_kmk.rag_client import rag_client

    rc = rag_client(force_logging=True)
    # list_collections should work (returns dict)
    res = rc.list_collections()
    assert isinstance(res, dict)

    # Ensure load_collection and chat return expected shapes
    rc.create_collection('testcol')
    rc.load_collection('testcol')
    chat_res = rc.chat('testcol', prompt='hello')
    assert chat_res.get('status') == 'OK'
    assert 'answer' in chat_res and 'retrieved_docs' in chat_res and 'prompt_len' in chat_res
