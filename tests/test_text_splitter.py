import pytest

from rag_kmk.knowledge_base.text_splitter import (
    convert_Pages_ChunkinChar,
    add_meta_data,
)


def test_convert_pages_chunkinchar_empty():
    chunks = convert_Pages_ChunkinChar([])
    assert isinstance(chunks, list)
    assert len(chunks) == 0


def test_convert_pages_chunkinchar_short_text():
    pages = ["Hello world."]
    chunks = convert_Pages_ChunkinChar(pages, chunk_size=1000, chunk_overlap=0)
    assert isinstance(chunks, list)
    assert len(chunks) >= 1


def test_add_meta_data_basic():
    tokens = ["a", "b", "c"]
    ids, metadatas = add_meta_data(tokens, title="doc.txt", initial_id=0)
    assert len(ids) == len(tokens)
    assert all(isinstance(i, str) for i in ids)
    assert len(metadatas) == len(tokens)
    assert metadatas[0]["document"] == "doc.txt"
