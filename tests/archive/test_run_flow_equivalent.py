import os
import types
import pytest
from pathlib import Path


def _sample_docs_path():
    p = Path(__file__).parent.parent / "tests" / "sample_documents"
    return p if p.exists() else None


@pytest.mark.skipif(not (Path('chromaDB').exists()), reason="no local chromaDB folder to test against")
def test_run_equivalent_persistent_only(monkeypatch, tmp_path):
    """Mimic run.py: load existing chromaDB directory and run pipeline with a fake client."""
    # Prepare: patch the real rag_kmk.chat_flow to use a fake client that has generate/close
    import rag_kmk.chat_flow as real_chat_flow

    class DummyClient:
        def generate(self, *args, **kwargs):
            return 'dummy'

        def close(self):
            pass

    called = {'ran': False}

    def fake_run_pipeline(client, kb, *args, **kwargs):
        # verify client is our DummyClient and kb is not None
        assert isinstance(client, DummyClient)
        assert kb is not None
        called['ran'] = True

    monkeypatch.setattr(real_chat_flow, 'build_chatBot', lambda cfg: DummyClient())
    monkeypatch.setattr(real_chat_flow, 'run_rag_pipeline', fake_run_pipeline)

    # Run the run.py-equivalent flow
    from rag_kmk.knowledge_base import build_knowledge_base
    from rag_kmk.vector_db import summarize_collection
    import rag_kmk.chat_flow as chat_flow

    # Use the real chromaDB folder in repo root
    # Attempt to open the existing repo chromaDB collection; if it cannot be opened, skip.
    from rag_kmk.knowledge_base.document_loader import load_knowledge_base
    kb, status = load_knowledge_base(collection_name='run_equiv', cfg={'vector_db': {'chromaDB_path': str(Path('chromaDB').resolve())}})
    if getattr(status, 'name', None) != 'OK':
        pytest.skip("Could not open repo chromaDB collection; skipping integration-style test")

    summarize_collection(kb)
    client = chat_flow.build_chatBot({})
    chat_flow.run_rag_pipeline(client, kb)

    assert called['ran'] is True
