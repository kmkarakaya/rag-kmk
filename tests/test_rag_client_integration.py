import os
import shutil
import json
import time
from pathlib import Path

import pytest


def test_rag_client_end_to_end(tmp_path, monkeypatch):
    # Prepare a temp chromaDB path
    chroma_dir = tmp_path / "chromaDB"
    chroma_dir.mkdir()

    # Prepare a small docs folder with a text file
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    doc_file = docs_dir / "sample.txt"
    doc_file.write_text("This is a tiny test document for rag-kmk integration test.")

    # Set package CONFIG to point to our temp chromaDB and ensure llm has no creds => NoOp LLM
    import importlib
    pkg = importlib.import_module('rag_kmk')
    pkg.CONFIG = {
        'vector_db': {'chromaDB_path': str(chroma_dir)},
        'llm': {},
        'knowledge_base': {'tokens_per_chunk': 128},
        'supported_file_types': ['.txt']
    }

    # Instantiate real rag_client and run through workflow
    from rag_kmk.rag_client import rag_client

    rc = rag_client()

    coll_name = 'it_test_coll'
    # create, load, ingest
    create_res = rc.create_collection(coll_name)
    assert create_res.get('status') in ('COLLECTION_CREATED', 'ALREADY_EXISTS', 'OK')

    load_res = rc.load_collection(coll_name)
    assert load_res.get('status') in ('COLLECTION_LOADED', 'OK')

    add_res = rc.add_doc(coll_name, doc_path=str(docs_dir))
    assert add_res.get('status') in ('OK',)

    # small pause to allow persistence if any
    time.sleep(0.1)

    # Chat should use NoOp LLM (since no API key/model configured) and return a placeholder
    chat_res = rc.chat(coll_name, prompt='What is this document about?')
    assert isinstance(chat_res, dict)
    assert chat_res.get('status') == 'OK'
    assert 'answer' in chat_res and 'retrieved_docs' in chat_res and 'prompt_len' in chat_res
    # NoOp LLM returns prefixed [NO-LLM]
    assert chat_res['answer'].startswith('[NO-LLM]')

    rc.close()
