import os
import sys
import types
import pytest

from rag_kmk.vector_db import database as vdb_database

def _install_fake_chromadb(monkeypatch, fail_get_collection=False):
	"""
	Install a minimal fake `chromadb` and `chromadb.config` into sys.modules.
	The fake client supports get_or_create_collection, create_collection and get_collection.
	If fail_get_collection is True, get_collection will raise to simulate missing collection.
	"""
	# Fake Settings factory for chromadb.config
	def Settings(**kwargs):
		return kwargs

	class FakeCollection:
		def __init__(self, name="col"):
			self.name = name
		def count(self):
			return 0
		def get(self, include=None):
			return {"ids": []}

	class FakeClient:
		def __init__(self, settings=None):
			self._settings = settings
		def get_or_create_collection(self, name=None):
			return FakeCollection(name or "col")
		def create_collection(self, name=None):
			return FakeCollection(name or "col")
		def get_collection(self, name):
			if fail_get_collection:
				raise Exception("collection not found")
			return FakeCollection(name or "col")

	# construct module & submodule
	mod = types.ModuleType("chromadb")
	config_mod = types.ModuleType("chromadb.config")
	config_mod.Settings = Settings
	mod.Client = FakeClient

	# inject into sys.modules
	monkeypatch.setitem(sys.modules, "chromadb", mod)
	monkeypatch.setitem(sys.modules, "chromadb.config", config_mod)


def test_create_and_open_persistent(tmp_path, monkeypatch):
	# Install fake chromadb (collection operations succeed)
	_install_fake_chromadb(monkeypatch, fail_get_collection=False)

	persist_dir = str(tmp_path / "chroma_persist")
	collection_name = "test_collection"

	# create new persistent DB and collection
	client, collection, status = vdb_database.create_chroma_client(
		collection_name=collection_name,
		chromaDB_path=persist_dir,
		create_new=True,
		config={}
	)
	assert status in (vdb_database.ChromaDBStatus.NEW_PERSISTENT_CREATED, vdb_database.ChromaDBStatus.OK)
	assert collection is not None

	# now open existing (create_new=False) should succeed
	# ensure the folder is non-empty so the factory doesn't treat it as missing
	os.makedirs(persist_dir, exist_ok=True)
	# create a small marker file so directory listing is non-empty
	with open(os.path.join(persist_dir, "marker.txt"), "w") as f:
		f.write("x")

	client2, collection2, status2 = vdb_database.create_chroma_client(
		collection_name=collection_name,
		chromaDB_path=persist_dir,
		create_new=False,
		config={}
	)
	assert status2 == vdb_database.ChromaDBStatus.OK
	assert collection2 is not None


def test_reject_missing_path(monkeypatch):
	# Install fake chromadb but passing None path should still be rejected by factory
	_install_fake_chromadb(monkeypatch)

	client, collection, status = vdb_database.create_chroma_client(
		collection_name="any",
		chromaDB_path=None,
		create_new=False,
		config={}
	)
	assert status in (vdb_database.ChromaDBStatus.ERROR, vdb_database.ChromaDBStatus.MISSING_PERSISTENT)


def test_open_missing_collection(tmp_path, monkeypatch):
	# Install fake chromadb configured to fail get_collection to simulate missing collection
	_install_fake_chromadb(monkeypatch, fail_get_collection=True)

	persist_dir = str(tmp_path / "chroma_missing_coll")
	os.makedirs(persist_dir, exist_ok=True)
	# create a small marker file so directory listing is non-empty (not MISSING_PERSISTENT)
	with open(os.path.join(persist_dir, "marker.txt"), "w") as f:
		f.write("x")

	client, collection, status = vdb_database.create_chroma_client(
		collection_name="nonexistent",
		chromaDB_path=persist_dir,
		create_new=False,
		config={}
	)
	assert status == vdb_database.ChromaDBStatus.MISSING_COLLECTION
