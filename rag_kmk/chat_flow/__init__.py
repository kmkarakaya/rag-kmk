from .llm_interface import build_chatBot, generate_LLM_answer, generateAnswer,run_rag_pipeline
from rag_kmk import CONFIG   


# Access the system_prompt value
system_prompt = CONFIG['llm']['settings']['system_prompt']
RAG_LLM = build_chatBot(system_prompt)

__all__ = ['build_rag_llm', 'generate_LLM_answer', 'RAG_LLM', 'generateAnswer', 'run_rag_pipeline'] 