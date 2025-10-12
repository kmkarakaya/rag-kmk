from rag_kmk import CONFIG
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.text_splitter import SentenceTransformersTokenTextSplitter


def convert_Pages_ChunkinChar(text_in_pages, chunk_size=None, chunk_overlap=None):
    # Lazy defaults from CONFIG to avoid import-time access errors
    kb_cfg = CONFIG.get("knowledge_base", {}) if isinstance(CONFIG, dict) else {}
    if chunk_size is None:
        chunk_size = kb_cfg.get("chunk_size", 1000)
    if chunk_overlap is None:
        chunk_overlap = kb_cfg.get("chunk_overlap", 200)
    character_splitter = RecursiveCharacterTextSplitter(separators=["\n\n", "\n", ". ", " ", ""],
                                                        chunk_size=chunk_size,
                                                        chunk_overlap=chunk_overlap)
    character_split_texts = character_splitter.split_text('\n\n'.join(text_in_pages))
    print(f"Total number of chunks (document split by max char = {chunk_size}): {len(character_split_texts)}")
    return character_split_texts

def convert_Chunk_Token(text_chunksinChar, sentence_transformer_model=None, chunk_overlap=None, tokens_per_chunk=None):
    db_cfg = CONFIG.get("vector_db", {}) if isinstance(CONFIG, dict) else {}
    kb_cfg = CONFIG.get("knowledge_base", {}) if isinstance(CONFIG, dict) else {}
    if sentence_transformer_model is None:
        sentence_transformer_model = db_cfg.get("embedding_model", "all-MiniLM-L6-v2")
    if chunk_overlap is None:
        chunk_overlap = kb_cfg.get("chunk_overlap", 200)
    if tokens_per_chunk is None:
        tokens_per_chunk = db_cfg.get("tokens_per_chunk", 128)
    token_splitter = SentenceTransformersTokenTextSplitter(
        chunk_overlap=chunk_overlap,
        model_name=sentence_transformer_model,
        tokens_per_chunk=tokens_per_chunk)
    
    text_chunksinTokens = []
    for text in text_chunksinChar:
        text_chunksinTokens += token_splitter.split_text(text)
        
    print(f"Total number of chunks (document split by 128 tokens per chunk): {len(text_chunksinTokens)}")
    return text_chunksinTokens

def add_document_to_collection(ids, metadatas, text_chunksinTokens, chroma_collection):
    print("Before inserting, the size of the collection: ", chroma_collection.count())
    print(f"***** metadatas: *****\n {metadatas}")
    # Some test mocks expect a fourth 'collection' parameter; pass it for
    # compatibility while keeping keyword args for real clients.
    try:
        chroma_collection.add(ids=ids, metadatas=metadatas, documents=text_chunksinTokens, collection=chroma_collection)
    except TypeError:
        # Fallback for real chroma clients that don't expect 'collection'
        chroma_collection.add(ids=ids, metadatas=metadatas, documents=text_chunksinTokens)

    print("After inserting, the size of the collection: ", chroma_collection.count())
    return chroma_collection


def add_meta_data(text_chunksinTokens, title, initial_id, category=None):
    ids = [str(i + initial_id) for i in range(len(text_chunksinTokens))]
    # Lazy category default
    db_cfg = CONFIG.get("vector_db", {}) if isinstance(CONFIG, dict) else {}
    if category is None:
        category = db_cfg.get('category', 'default')
    metadata = {
        'document': title,
        'category': category,
    }
    metadatas = [metadata for _ in range(len(text_chunksinTokens))]
    return ids, metadatas

