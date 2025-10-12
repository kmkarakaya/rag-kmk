"""Custom exceptions for rag_kmk."""
class MissingAPIKey(Exception):
    """Raised when an API key is required but not found."""
    pass


class LLMInitError(Exception):
    """Raised when an LLM client fails to initialize."""
    pass


class IndexingError(Exception):
    """Raised for errors during indexing or building knowledge base."""
    pass


class GenerationError(Exception):
    """Raised when generation from the LLM fails irrecoverably."""
    pass
