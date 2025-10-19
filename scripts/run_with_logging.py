"""Example helper to run the sample runner with logging initialized.

Usage:
    python scripts\run_with_logging.py

This will initialize logging (console + rotating file) using the package helper
and then import and run the top-level `run.py` script.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from rag_kmk import logging_setup as ls
    ls.init_logging_from_config(None, force=True)
except Exception:
    # best-effort: if logging helper missing, continue without failing
    pass

import run
