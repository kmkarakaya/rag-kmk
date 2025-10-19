import sys, os
import logging
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from rag_kmk.knowledge_base import build_knowledge_base

log = logging.getLogger(__name__)

kb, status = build_knowledge_base(document_directory_path=r'.\\tests\\sample_documents', chromaDB_path=r'.\\chromaDB')
log.info('returned status: %s', status)
log.info('kb is None? %s', kb is None)
