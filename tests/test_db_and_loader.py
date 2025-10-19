import sys
import types
import os
import pytest

from rag_kmk.vector_db import database as vdb_database
from rag_kmk.knowledge_base import document_loader


def test_create_chroma_client_missing_persistent(tmp_path):
	# Path that doesn't exist -> MISSING_PERSISTENT when create_new=False
	nonexistent = tmp_path / "does_not_exist"
	client, collection, status = vdb_database.create_chroma_client("col", str(nonexistent), create_new=False)
	assert client is None
	assert collection is None
	assert status == vdb_database.ChromaDBStatus.MISSING_PERSISTENT


def test_resolve_collection_count_variants():
	# Variant 1: count() -> int
	class C1:
		def count(self):
			return 5

	assert document_loader._resolve_collection_count(C1()) == 5

	# Variant 2: count() -> dict
	class C2:
		def count(self):
			return {"count": 3}

	assert document_loader._resolve_collection_count(C2()) == 3

	# Variant 3: count() raises TypeError when called without args, but works with {}
	class C3:
		def count(self, arg=None):
			if arg is None:
				raise TypeError("no arg")
			return {"count": 7}

	assert document_loader._resolve_collection_count(C3()) == 7

	# Variant 4: no count(), but get() returns ids list
	class C4:
		def get(self, include=None):
			return {"ids": ["a", "b", "c"]}

	assert document_loader._resolve_collection_count(C4()) == 3
