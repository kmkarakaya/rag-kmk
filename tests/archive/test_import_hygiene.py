import importlib
import sys
from unittest import mock


def test_import_does_not_instantiate_clients(monkeypatch):
    """Importing the package should not attempt to import or initialize LLM SDKs.

    We simulate that google.genai import will raise if attempted; importing
    rag_kmk must not raise.
    """
    # Make 'google.genai' import raise if attempted. Use a real module object
    # with a __getattr__ that raises to simulate failure on access.
    import types
    google_mod = types.ModuleType('google')
    genai_mod = types.ModuleType('google.genai')
    def _raise(name):
        raise RuntimeError('should not import google.genai at import time')
    genai_mod.__getattr__ = _raise
    # Insert into sys.modules so imports of google or google.genai hit our stubs
    sys.modules['google'] = google_mod
    sys.modules['google.genai'] = genai_mod

    # Now import the package fresh
    if 'rag_kmk' in sys.modules:
        del sys.modules['rag_kmk']
    import importlib
    importlib.invalidate_caches()

    # Should not raise
    import rag_kmk
    assert hasattr(rag_kmk, 'initialize_rag')
