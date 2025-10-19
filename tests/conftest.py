"""Minimal fixtures for the kept test suite.

This `conftest.py` provides small, real fixtures used by the
integration/unit tests that remain in the repository. Legacy heavy
fixtures and fake chromadb shims were intentionally removed.
"""

import os
import sys
import pytest

# Make package importable when running tests from tests/ directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rag_kmk import CONFIG


@pytest.fixture(scope='session')
def sample_docs_dir():
    return os.path.join(os.path.dirname(__file__), 'sample_documents')


@pytest.fixture
def tmp_chroma_dir(tmp_path, monkeypatch):
    path = tmp_path / "chromaDB"
    path.mkdir()
    # Override package CONFIG for tests that read from CONFIG
    monkeypatch.setitem(CONFIG, 'vector_db', CONFIG.get('vector_db', {}))
    CONFIG['vector_db']['chromaDB_path'] = str(path)
    yield str(path)

