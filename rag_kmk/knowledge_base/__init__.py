from rag_kmk.utils import load_config
from .document_loader import load_documents
from .text_splitter import split_text
from .vectorizer import vectorize_chunks

def build_knowledge_base(file_list, config=None):
    if config is None:
        config = load_config()

    kb_config = config.get('knowledge_base', {})
    chunk_size = kb_config.get('chunk_size', 1000)  # Default value if not in config
    chunk_overlap = kb_config.get('chunk_overlap', 200)  # Default value if not in config
    embedding_model = kb_config.get('embedding_model', 'default_model')  # Default value if not in config
    
    documents = load_documents(file_list, config)
    chunks = split_text(documents, chunk_size, chunk_overlap)
    vectors = vectorize_chunks(chunks, embedding_model)
    return vectors

__all__ = ['build_knowledge_base']