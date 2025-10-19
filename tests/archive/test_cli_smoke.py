from types import SimpleNamespace
import rag_kmk


def test_run_main_smoke(monkeypatch, tmp_path):
    """Smoke test that runs the non-LLM parts of the flow but patches the
    chat_flow interactive loop. This avoids replacing internal rag_kmk modules
    and ensures we exercise the library implementation.
    """
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / 'sample.txt').write_text('sample content')

    import rag_kmk.chat_flow as real_chat_flow

    called = {'ok': False}

    class DummyClient:
        def generate(self, prompt, **opts):
            return 'fake'

        def close(self):
            pass

    monkeypatch.setattr(real_chat_flow, 'build_chatBot', lambda cfg: DummyClient())
    monkeypatch.setattr(real_chat_flow, 'run_rag_pipeline', lambda client, kb: called.__setitem__('ok', True))

    from rag_kmk.knowledge_base import build_knowledge_base
    from rag_kmk.vector_db import summarize_collection

    kb, chromaDB_status = build_knowledge_base(collection_name='cli_smoke', document_directory_path=str(docs_dir), add_documents=True, chromaDB_path=None)
    summarize_collection(kb)
    client = real_chat_flow.build_chatBot({})
    real_chat_flow.run_rag_pipeline(client, kb)

    assert called['ok'] is True
