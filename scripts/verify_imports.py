import importlib
import logging
import sys

log = logging.getLogger(__name__)

modules = [
    ("numpy", "numpy"),
    ("PyYAML", "yaml"),
    ("PyMuPDF", "fitz"),
    ("langchain", "langchain"),
    ("langchain-core", "langchain_core"),
    ("sentence-transformers", "sentence_transformers"),
    # google-genai installs a `google` package with a `genai` submodule (import as `google.genai`)
    ("google-genai", "google.genai"),
    ("chromadb", "chromadb"),
    ("streamlit", "streamlit"),
    ("python-docx", "docx"),
    ("google.protobuf", "google.protobuf"),
    ("packaging", "packaging"),
    ("torch", "torch"),
    ("lxml", "lxml"),
    ("blinker", "blinker"),
    ("overrides", "overrides"),
]

results = {}
for pkg_name, mod_name in modules:
    try:
        importlib.import_module(mod_name)
        results[pkg_name] = "OK"
    except Exception as e:
        results[pkg_name] = f"ERROR: {type(e).__name__}: {e}"

max_name_len = max(len(k) for k in results.keys())
for pkg, res in results.items():
    log.info(f"{pkg.ljust(max_name_len)} : {res}")

# exit with non-zero if any errors
if any(not r.startswith("OK") for r in results.values()):
    sys.exit(1)
