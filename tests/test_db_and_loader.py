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

def test_create_chroma_client_create_new_already_exists(tmp_path, monkeypatch):
	# Prepare a persistent folder (create_new will create it) and mock chromadb to simulate existing collection
	chroma_path = tmp_path / "chroma"
	# ensure folder exists since create_new will call makedirs; create now to avoid race
	os.makedirs(str(chroma_path), exist_ok=True)

	class FakeClient:
		def __init__(self, path=None):
			self._path = path
		def list_collections(self):
			# Simulate list containing the requested collection name
			return ["existing_collection"]

	def persistent_client_factory(path=None):
		return FakeClient(path=path)

	# Create a fake chromadb module with PersistentClient attribute
	fake_chromadb = types.SimpleNamespace(PersistentClient=persistent_client_factory)
	# Inject into sys.modules so import chromadb resolves to our fake
	orig = sys.modules.get("chromadb")
	sys.modules["chromadb"] = fake_chromadb

	try:
		client, collection, status = vdb_database.create_chroma_client("existing_collection", str(chroma_path), create_new=True)
		assert client is None and collection is None
		assert status == vdb_database.ChromaDBStatus.ALREADY_EXISTS
	finally:
		# restore original module (if any)
		if orig is not None:
			sys.modules["chromadb"] = orig
		else:
			sys.modules.pop("chromadb", None)

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
