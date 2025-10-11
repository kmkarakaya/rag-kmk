import os
from pathlib import Path

from rag_kmk.knowledge_base.document_loader import build_knowledge_base


def test_build_knowledge_base_with_mock(mock_chroma_client, tmp_path):
    # create a tiny text file
    docs = tmp_path / 'docs'
    docs.mkdir()
    f = docs / 'sample.txt'
    f.write_text('Hello world. This is a test document.')

    collection, status = build_knowledge_base(document_directory_path=str(docs), chromaDB_path=None)

    # With the mocked create_chroma_client, build_knowledge_base returns the fake collection and status
    assert status is not None
    # collection should expose count() method (mocked)
    assert hasattr(collection, 'count')
