import importlib
import logging
import os
import time
from typing import Optional

log = logging.getLogger(__name__)
try:
	# Local helper; optional
	from rag_kmk import logging_setup as _logging_setup
except Exception:
	_logging_setup = None

class rag_client:
	"""
	Minimal, robust rag_client wrapper.
	Lazy-imports heavy modules and delegates to rag_kmk internals.
	Designed to work with the existing run.py unchanged.
	"""

	def __init__(self, config_path: Optional[str] = None, force_logging: bool = False):
		# Resolve configuration from the package-level CONFIG if present;
		# otherwise try to load via the config module.
		pkg = importlib.import_module("rag_kmk")
		cfg = getattr(pkg, "CONFIG", None)
		if (not isinstance(cfg, dict)) or cfg is None:
			try:
				cfg_mod = importlib.import_module("rag_kmk.config.config")
				cfg = cfg_mod.load_config(config_path)
			except Exception:
				cfg = {}
		self.config = cfg or {}

		# Initialize logging if requested by env var or explicit flag.
		# This is non-invasive by default: it only configures logging when
		# RAG_KMK_AUTOLOG=1 or when force_logging=True is passed.
		if getattr(_logging_setup, 'init_logging_from_config', None):
			try:
				if os.getenv('RAG_KMK_AUTOLOG') == '1' or force_logging:
					_logging_setup.init_logging_from_config(self.config, force=force_logging)
			except Exception:
				# Do not fail construction if logging setup fails
				pass
		# clients/handles
		self.client = None
		self.client_status = None
		self.client_error = None
		self._collection_handles = {}
		# lazily initialize DB/LLM clients
		try:
			self._init_clients()
		except Exception as e:
			log.exception("rag_client: failed to init clients: %s", e)

	def _init_clients(self):
		# Lazy import vector db helper
		vdb = importlib.import_module("rag_kmk.vector_db.database")
		chroma_path = self.config.get("vector_db", {}).get("chromaDB_path")
		client_result = vdb.create_chromadb_client(chroma_path)
		self.client = client_result.get("client")
		self.client_status = client_result.get("status")
		self.client_error = client_result.get("error")
		# Do NOT initialize LLM client here; defer to lazy builder to avoid
		# heavy imports or network calls at package init time.
		self.llm = None

	# --- VECTOR DB helpers (wrap vdb functions) ---
	def list_collections(self):
		try:
			vdb = importlib.import_module("rag_kmk.vector_db.database")
			if self.client is None:
				return {"status": "ERROR", "collections": [], "error": "ChromaDB client not initialized."}
			return vdb.list_collection_names(self.client)
		except Exception as e:
			log.exception("list_collections failed: %s", e)
			return {"status": "ERROR", "collections": [], "error": str(e)}

	def create_collection(self, collection_name: str):
		try:
			vdb = importlib.import_module("rag_kmk.vector_db.database")
			if self.client is None:
				return {"status": "ERROR", "collection_name": None, "error": "ChromaDB client not initialized."}
			result, collection = vdb.create_collection(self.client, collection_name)
			col_name = getattr(collection, "name", collection_name) if collection is not None else collection_name
			if collection is not None:
				self._collection_handles[col_name] = collection
			return {
				"status": result.get("status"),
				"collection_name": col_name,
				"error": result.get("error"),
			}
		except Exception as e:
			log.exception("create_collection failed: %s", e)
			return {"status": "ERROR", "collection_name": None, "error": str(e)}

	def load_collection(self, collection_name: str):
		try:
			vdb = importlib.import_module("rag_kmk.vector_db.database")
			if self.client is None:
				return {"status": "ERROR", "collection_name": None, "error": "ChromaDB client not initialized."}
			result, collection = vdb.load_collection(self.client, collection_name)
			col_name = getattr(collection, "name", collection_name) if collection is not None else None
			if collection is not None:
				self._collection_handles[col_name] = collection
			return {"status": result.get("status"), "collection_name": col_name, "error": result.get("error")}
		except Exception as e:
			log.exception("load_collection failed: %s", e)
			return {"status": "ERROR", "collection_name": None, "error": str(e)}

	def get_collection_handle(self, collection_name: str):
		return self._collection_handles.get(collection_name)

	def summarize_collection(self, collection_name_or_handle):
		try:
			vdb = importlib.import_module("rag_kmk.vector_db.database")
			# if a name string was provided, load or use internal handle
			if isinstance(collection_name_or_handle, str):
				col = self.get_collection_handle(collection_name_or_handle)
				if col is None:
					res = self.load_collection(collection_name_or_handle)
					if res.get("collection_name") is None:
						return {"status": "ERROR", "summary": {}, "error": res.get("error")}
					col = self.get_collection_handle(collection_name_or_handle)
			else:
				col = collection_name_or_handle
			if col is None:
				return {"status": "ERROR", "summary": {}, "error": "Collection not available"}
			return vdb.summarize_collection(col)
		except Exception as e:
			log.exception("summarize_collection failed: %s", e)
			return {"status": "ERROR", "summary": {}, "error": str(e)}

	def delete_collection(self, collection_name: str):
		try:
			vdb = importlib.import_module("rag_kmk.vector_db.database")
			if self.client is None:
				return {"status": "ERROR", "success": False, "error": "ChromaDB client not initialized."}
			result = vdb.delete_collection(self.client, collection_name)
			# cleanup handle if success
			if isinstance(result, dict) and result.get("success"):
				self._collection_handles.pop(collection_name, None)
			return result
		except Exception as e:
			log.exception("delete_collection failed: %s", e)
			return {"status": "ERROR", "success": False, "error": str(e)}

	# --- KNOWLEDGE BASE ingestion ---
	def add_doc(self, collection_name: str, doc_path: str, **kwargs):
		"""
		High-level ingestion entrypoint used by run.py.
		Ensures collection handle exists (load/create) and delegates to the low-level ingestion helper.
		"""
		# Debug: suppressed print to reduce console noise
		# print(f"[rag-kmk][rag_client] add_doc START collection={collection_name} doc_path={doc_path}", flush=True)
		log.info("rag_client.add_doc START collection=%s doc_path=%s", collection_name, doc_path)
		try:
			# ensure client present
			if self.client is None:
				return {"status": "ERROR", "collection_name": None, "error": "ChromaDB client not initialized."}

			# obtain collection handle
			coll = self.get_collection_handle(collection_name)
			if coll is None:
				load_res = self.load_collection(collection_name)
				if load_res.get("collection_name") is None:
					# try create
					create_res = self.create_collection(collection_name)
					if create_res.get("collection_name") is None:
						return {"status": "ERROR", "collection_name": None, "error": create_res.get("error")}
				coll = self.get_collection_handle(collection_name)
				if coll is None:
					return {"status": "ERROR", "collection_name": None, "error": "Failed to obtain collection handle."}

			# delegate to low-level ingestion
			kb_loader = importlib.import_module("rag_kmk.knowledge_base.document_loader")
			start_ts = time.perf_counter()
			files_processed, errors = kb_loader.load_and_add_documents(coll, doc_path, self.config, **kwargs)
			duration = time.perf_counter() - start_ts
			# Debug: suppressed print to reduce console noise
			# print(f"[rag-kmk][rag_client] load_and_add_documents returned: processed={files_processed} errors={errors} duration={duration:.3f}s", flush=True)
			log.info("rag_client.add_doc ingestion finished for %s processed=%s in %.3fs", collection_name, files_processed, duration)
			if files_processed:
				return {"status": "OK", "collection_name": collection_name}
			else:
				return {"status": "ERROR", "collection_name": collection_name, "error": "; ".join(errors) if errors else "No files processed"}
		except Exception as e:
			log.exception("rag_client.add_doc failed: %s", e)
			return {"status": "ERROR", "collection_name": None, "error": str(e)}

	# --- CONFIG helpers ---
	def reload_config(self, config_path: Optional[str] = None):
		try:
			cfg_mod = importlib.import_module("rag_kmk.config.config")
			self.config = cfg_mod.load_config(config_path)
			pkg = importlib.import_module("rag_kmk")
			pkg.CONFIG = self.config
			# re-init clients with new config
			self._init_clients()
			return {"status": "OK", "config": self.config}
		except Exception as e:
			log.exception("reload_config failed: %s", e)
			return {"status": "ERROR", "error": str(e)}

	def mask_config(self, keys=("api_key", "api_key_env_var")):
		try:
			cfg_mod = importlib.import_module("rag_kmk.config.config")
			return cfg_mod.mask_config(self.config, keys=keys)
		except Exception as e:
			log.exception("mask_config failed: %s", e)
			return {"status": "ERROR", "error": str(e)}

	# --- CHAT FLOW helpers ---
	def chat(self, collection_name: str, prompt: str, n_results: int = 5, timeout_seconds: int = 30, **kwargs):
		"""
		Single unified chat entrypoint.
		- Ensures the collection is loaded
		- Lazily initializes the LLM client (using rag_kmk.chat_flow.llm_interface)
		- Retrieves relevant chunks from the collection and appends them to the prompt
		- Calls the LLM with timeout enforcement and returns the answer and retrieved docs
		"""
		try:
			# Ensure collection is available
			if self.get_collection_handle(collection_name) is None:
				load_res = self.load_collection(collection_name)
				if load_res.get("collection_name") is None:
					return {"status": "ERROR", "error": load_res.get("error")}

			# Ensure chroma client present
			if self.client is None:
				return {"status": "ERROR", "error": "ChromaDB client not initialized."}

			col = self.get_collection_handle(collection_name)

			# Lazily initialize LLM client
			llm_mod = importlib.import_module("rag_kmk.chat_flow.llm_interface")
			if not getattr(self, 'llm', None):
				try:
					self.llm = llm_mod.build_chatBot(self.config.get('llm', {}))
				except Exception as e:
					log.exception("chat: failed to initialize LLM: %s", e)
					return {"status": "ERROR", "error": f"LLM initialization failed: {e}"}

			# Retrieve context from vector DB
			retrieved_docs = []
			try:
				from rag_kmk.vector_db import query as vq
				docs = vq.retrieve_chunks(col, prompt, n_results=n_results, return_only_docs=True)
				if docs:
					retrieved_docs = docs
					context = '\n'.join(retrieved_docs)
				else:
					context = ''
			except Exception as e:
				log.exception("chat: retrieval failed: %s", e)
				context = ''

			# Assemble final prompt
			final_prompt = prompt + ('\n EXCERPTS:\n' + context if context else '')

			# Generate answer with timeout enforcement
			try:
				answer_text = llm_mod.generate_LLM_answer(self.llm, final_prompt, timeout_seconds=timeout_seconds)
			except Exception as e:
				log.exception("chat: LLM generation failed: %s", e)
				return {"status": "ERROR", "error": str(e), "retrieved_docs": retrieved_docs}

			return {"status": "OK", "answer": answer_text, "retrieved_docs": retrieved_docs, "prompt_len": len(final_prompt)}
		except Exception as e:
			log.exception("chat failed: %s", e)
			return {"status": "ERROR", "error": str(e)}

	def close(self):
		try:
			if self.llm and hasattr(self.llm, "close"):
				try:
					self.llm.close()
				except Exception:
					pass
			# If the chroma client has a close/terminate method, try it
			if self.client and hasattr(self.client, "close"):
				try:
					self.client.close()
				except Exception:
					pass
		except Exception:
			pass
