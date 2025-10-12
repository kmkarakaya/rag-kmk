from .llm_interface import build_chatBot, generate_LLM_answer, generateAnswer, run_rag_pipeline

# Backwards-compatible global placeholder. Older code expects `RAG_LLM` to be
# importable; keep it as None so callers can assign a client at runtime.
RAG_LLM = None

# Do not create a real global RAG_LLM at import time; callers should call
# `build_chatBot()` explicitly and assign the result to this symbol if needed.
__all__ = ['build_chatBot', 'generate_LLM_answer', 'generateAnswer', 'run_rag_pipeline', 'RAG_LLM']