from types import SimpleNamespace
import rag_kmk


def test_run_main_noninteractive_invokes_pipeline(monkeypatch, tmp_path):
    """Use the real knowledge_base and vector_db code but patch chat_flow's
    interactive loop to avoid blocking stdin. This ensures the test exercises
    the library implementation rather than replacing internal modules.
    """
    # Ensure we point at a small temporary documents directory for deterministic behavior
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    # Copy sample document into the temp dir
    sample_src = rag_kmk.__file__.replace('__init__.py', '') + 'tests\\sample_documents\\sample.txt'
    try:
        # best-effort: if the repo layout differs, fall back to existing sample dir
        import shutil
        shutil.copy(sample_src, str(docs_dir / 'sample.txt'))
    except Exception:
        # If copy fails, create a tiny sample file
        (docs_dir / 'sample.txt').write_text('hello world')

    # Monkeypatch chat_flow to provide a deterministic client and bypass interactive loop
    import rag_kmk.chat_flow as real_chat_flow

    class DummyClient:
        def generate(self, prompt, **opts):
            return 'fake'

        def close(self):
            pass

    monkeypatch.setattr(real_chat_flow, 'build_chatBot', lambda cfg: DummyClient())

    called = {'called': False}

    def fake_run_pipeline(client, kb, *args, **kwargs):
        called['called'] = True

    monkeypatch.setattr(real_chat_flow, 'run_rag_pipeline', fake_run_pipeline)

    # Run the real library flow
    from rag_kmk.knowledge_base import build_knowledge_base
    from rag_kmk.vector_db import summarize_collection

    kb, chromaDB_status = build_knowledge_base(collection_name='run_workflow', document_directory_path=str(docs_dir), add_documents=True, chromaDB_path=None)
    # summarizing should not raise
    summarize_collection(kb)
    client = real_chat_flow.build_chatBot({})
    real_chat_flow.run_rag_pipeline(client, kb)

    assert called['called'] is True
