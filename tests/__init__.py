"""PRUNED: tests package now contains only integration tests."""
"""Unit test package for rag_kmk."""
import os
import sys

# Ensure repository root is importable for tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Keep __all__ minimal; tests should import what they need directly
__all__ = []