"""Unit test package for rag_kmk."""
import os
import sys

# Add the parent directory to the Python path
# This allows the tests to import the rag_kmk package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# You can optionally import commonly used testing utilities
import unittest
from unittest.mock import Mock, patch

# You might want to set up a test configuration
from rag_kmk import initialize_rag

# Load the test configuration directly
TEST_CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'test_config.yaml')
with open(TEST_CONFIG_PATH, 'r') as config_file:
    TEST_CONFIG = yaml.safe_load(config_file)

# You could define some helper functions for your tests
def create_test_documents():
    # Create and return some sample documents for testing
    pass

def create_test_vector_db():
    # Create and return a test vector database
    pass

# Expose what you want to be easily accessible in your test files
__all__ = ['unittest', 'Mock', 'patch', 'TEST_CONFIG', 'create_test_documents', 'create_test_vector_db']