from .prompt_handler import handle_prompt
from .llm_interface import RAGLLM

def build_rag_llm(vector_db, config):
    llm_config = config['llm']
    rag_config = config['rag']
    return RAGLLM(vector_db, llm_config, rag_config)

__all__ = ['build_rag_llm']