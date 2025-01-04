"""Top-level package for rag-kmk."""

__author__ = """Murat Karakaya"""
__email__ = "kmkarakaya@gmail.com"
__version__ = "0.0.40"


from .config.config import load_config
import os
import yaml

# Define the initialize_rag function
def initialize_rag(custom_config_path=None):
    """
        This module initialization ensures that rag-kmk is properly set up upon import.
        Initialize the RAG system with either the default or a custom config.
    """
    if custom_config_path:
        if os.path.isfile(custom_config_path):
            try:
                with open(custom_config_path, 'r') as f:
                    yaml.safe_load(f) #Attempt to parse YAML, raises error if invalid
                print(f"Custom config file uploading from {custom_config_path}")
                CONFIG = load_config(custom_config_path)
                return CONFIG
            except yaml.YAMLError as e:
                print(f"Error parsing YAML config file: {e}. Using default config.")
                return load_config()
            except Exception as e:
                print(f"An unexpected error occurred while loading the config file: {e}. Using default config.")
                return load_config()
        else:
            print("Default config file uploading...")
    CONFIG = load_config()
    return CONFIG

# Load the configuration when the module is imported
try:
    CONFIG = initialize_rag("./config.yaml")
    print(f"RAG-KMK initialized with config")
except Exception as e:
    print(f"Error initializing rag-kmk module: {e}")



__all__ = ['build_knowledge_base', 'build_vector_db', 'build_rag_llm', 'initialize_rag', 'CONFIG']
