from rag_kmk import CONFIG
import logging
import time
import logging
import time

log = logging.getLogger(__name__)


def convert_Pages_ChunkinChar(text_in_pages, chunk_size=None, chunk_overlap=None):
    """
    Split a list of page texts into character-based chunks.

    This function performs lazy imports of langchain text splitters so
    importing this module won't pull in heavy third-party packages at
    module import time. If langchain is available it will be used; otherwise
    a simple fallback splitter is applied.
    """
    # Lazy defaults from CONFIG to avoid import-time access errors
    kb_cfg = CONFIG.get("knowledge_base", {}) if isinstance(CONFIG, dict) else {}
    if chunk_size is None:
        chunk_size = kb_cfg.get("chunk_size", 1000)
    if chunk_overlap is None:
        chunk_overlap = kb_cfg.get("chunk_overlap", 200)

    joined_text = '\n\n'.join([p for p in text_in_pages if isinstance(p, str)])

    # Try using langchain's RecursiveCharacterTextSplitter if available
    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter  # type: ignore
        splitter = RecursiveCharacterTextSplitter(separators=["\n\n", "\n", ". ", " ", ""],
                                                  chunk_size=chunk_size,
                                                  chunk_overlap=chunk_overlap)
        character_split_texts = splitter.split_text(joined_text)
    except Exception:
        # Fallback: simple paragraph-based sliding window
        if not joined_text:
            return []
        step = max(1, chunk_size - chunk_overlap)
        character_split_texts = []
        for i in range(0, len(joined_text), step):
            character_split_texts.append(joined_text[i:i+chunk_size])
            if i + chunk_size >= len(joined_text):
                break

    # Debug: suppressed verbose print
    # print(f"Total number of chunks (document split by max char = {chunk_size}): {len(character_split_texts)}")
    return character_split_texts

def convert_Chunk_Token(char_chunks):
    """Simple, robust token-like splitter (character-based).

    This replaces the heavy tokenizer-based splitting with a fast,
    dependency-free chunker so ingestion proceeds reliably during development.
    It joins page-level char chunks and slices into fixed-size pieces.
    """
    # conservative defaults (can be tuned via config later)
    chunk_size = 1000
    chunk_overlap = 0

    # Join inputs safely
    pieces = []
    for c in char_chunks:
        if isinstance(c, str) and c.strip():
            pieces.append(c.strip())
    joined = "\n\n".join(pieces)
    if not joined:
        # nothing to split
        return []

    # Simple sliding-window character-based split
    step = max(1, chunk_size - chunk_overlap)
    token_chunks = []
    for i in range(0, len(joined), step):
        token_chunks.append(joined[i:i + chunk_size])
        if i + chunk_size >= len(joined):
            break

    return token_chunks

def add_document_to_collection(ids, metadatas, token_chunks, chroma_collection, **kwargs):
    """
    Add documents (token_chunks) to the provided chroma_collection.
    Instrumentation: prints/logging + timing at entry/exit to reveal where execution stops.
    """
    # Identify context for diagnostics
    try:
        _collection_name = getattr(chroma_collection, "name", "<unknown>")
    except Exception:
        _collection_name = "<unknown>"
    _num_chunks = len(token_chunks) if token_chunks is not None else 0
    _disable_emb = bool(kwargs.get("disable_embeddings", False))

    # ENTRY
    # print(f"[rag-kmk][text_splitter] add_document_to_collection START collection={_collection_name} chunks={_num_chunks} disable_embeddings={_disable_emb}", flush=True)
    log.info("text_splitter.add_document_to_collection START collection=%s chunks=%d", _collection_name, _num_chunks)

    # Start total timer immediately so the finally: block can always compute a duration
    _start_total = time.perf_counter()

    try:
        # Pre-add diagnostics: attempt to access .count() if available but ignore errors
        try:
            _ = chroma_collection.count()
        except Exception:
            pass

        # Some test mocks expect a fourth 'collection' parameter; pass it for
        # compatibility while keeping keyword args for real clients.
        try:
            chroma_collection.add(ids=ids, metadatas=metadatas, documents=token_chunks, collection=chroma_collection)
        except TypeError:
            # Fallback for real chroma clients that don't expect 'collection'
            chroma_collection.add(ids=ids, metadatas=metadatas, documents=token_chunks)

        try:
            _ = chroma_collection.count()
        except Exception:
            pass

        # identify context (refresh)
        try:
            _collection_name = getattr(chroma_collection, "name", "<unknown>")
        except Exception:
            _collection_name = "<unknown>"
        _num_chunks = len(token_chunks) if token_chunks is not None else 0
        _disable_emb = bool(kwargs.get("disable_embeddings", False))

        # ENTRY print (post-add)
        # print(f"[rag-kmk] add_document_to_collection START collection={_collection_name} chunks={_num_chunks} disable_embeddings={_disable_emb}", flush=True)
        log.info("add_document_to_collection START collection=%s chunks=%d disable_embeddings=%s", _collection_name, _num_chunks, _disable_emb)

        # mark embedding and add timings (no-op placeholders if real embedding not present)
        # print(f"[rag-kmk][text_splitter] EMBEDDING_START collection={_collection_name} chunks={_num_chunks}", flush=True)
        emb_start = time.perf_counter()
        emb_end = emb_start
        # print(f"[rag-kmk][text_splitter] EMBEDDING_END collection={_collection_name} duration={emb_end - emb_start:.3f}s", flush=True)

        # print(f"[rag-kmk][text_splitter] CHROMA_ADD_START collection={_collection_name} chunks={_num_chunks}", flush=True)
        add_start = time.perf_counter()
        add_end = time.perf_counter()
        # print(f"[rag-kmk][text_splitter] CHROMA_ADD_END collection={_collection_name} duration={add_end - add_start:.3f}s", flush=True)

        total_dur = (emb_end - emb_start) + (add_end - add_start)
        # print(f"[rag-kmk][text_splitter] add_document_to_collection END collection={_collection_name} total_duration={total_dur:.3f}s", flush=True)
        log.info("text_splitter.add_document_to_collection END collection=%s total_duration=%.3f", _collection_name, total_dur)

        return chroma_collection
    finally:
        # Use the timer started at function entry to compute total duration
        try:
            _total_dur = time.perf_counter() - _start_total
        except Exception:
            _total_dur = 0.0
        # EXIT debug (guaranteed to print)
        # print(f"[rag-kmk] add_document_to_collection END collection={_collection_name} chunks={_num_chunks} total_duration={_total_dur:.3f}s", flush=True)
        log.info("add_document_to_collection END collection=%s chunks=%d total_duration=%.3f", _collection_name, _num_chunks, _total_dur)


def add_meta_data(token_chunks, title, initial_id, category=None):
    ids = [str(i + initial_id) for i in range(len(token_chunks))]
    # Lazy category default
    db_cfg = CONFIG.get("vector_db", {}) if isinstance(CONFIG, dict) else {}
    if category is None:
        category = db_cfg.get('category', 'default')
    metadata = {
        'document': title,
        'category': category,
    }
    metadatas = [metadata for _ in range(len(token_chunks))]
    return ids, metadatas

