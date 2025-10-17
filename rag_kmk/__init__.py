"""Top-level package for rag-kmk.

This module intentionally avoids performing any network calls or reading
environment files at import time. Call `initialize_rag()` to load configuration
explicitly at runtime.
"""

__author__ = "Murat Karakaya"
__email__ = "kmkarakaya@gmail.com"
__version__ = "0.0.54"

from .config.config import load_config, mask_config

# Do NOT load configuration or build network clients at import time. Provide an
# explicit initializer that callers can use to load or override configuration.
def initialize_rag(custom_config_path=None):
    """Load and return configuration from the repository or a custom path.

    This function is intentionally side-effect free (it returns the config
    dict). Callers who need a module-level `CONFIG` may assign the returned
    value to `rag_kmk.CONFIG` explicitly.
    """
    return load_config(custom_config_path)

# Backwards-compatible behavior: try to populate CONFIG at import time from the
# repository config file. Wrap in try/except to avoid hard failures on import.
try:
    CONFIG = load_config()
except Exception:
    CONFIG = {}

__all__ = ["initialize_rag", "CONFIG", "load_config", "mask_config"]
