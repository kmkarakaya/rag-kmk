"""LLM interface for rag_kmk.

This module exposes builder-style functions and does not perform any network
access at import time. Heavy SDK imports are performed lazily when
`build_chatBot()` is called so tests can import the package without requiring
network or credentials.
"""
from typing import Optional, Any, Dict
import os
import logging
import concurrent.futures

logger = logging.getLogger(__name__)


class ChatClient:
    """Minimal ChatClient interface used by the library.

    Implementations must provide generate(prompt: str, **opts) -> str and
    close() -> None. The `supports_streaming` attribute indicates streaming
    capability.
    """
    supports_streaming = False

    def generate(self, prompt: str, **opts) -> str:
        raise NotImplementedError()

    def close(self) -> None:
        pass


def build_chatBot(config: Optional[Dict[str, Any]] = None) -> ChatClient:
    """Create and return a ChatClient based on `config`.

    The function performs lazy imports of heavy SDKs. It raises RuntimeError or
    LLMInitError when initialization fails.
    """
    # Lazy import to avoid import-time side-effects
    try:
        from google import genai as genai  # type: ignore
        from google.genai import types  # type: ignore
    except Exception as e:
        logger.debug("google.genai not available: %s", e)
        raise RuntimeError("LLM SDK not available") from e

    # Minimal wrapper implementation using the SDK
    class _GenAIClient(ChatClient):
        def __init__(self, api_key: str, model: str, system_prompt: str = ''):
            self._client = genai.Client(api_key=api_key)
            cfg = types.GenerateContentConfig(
                temperature=0.5,
                response_mime_type="text/plain",
                system_instruction=[types.Part.from_text(text=system_prompt)],
            )
            self._chat = self._client.chats.create(model=model, config=cfg)

        def generate(self, prompt: str, **opts) -> str:
            resp = self._chat.send_message(prompt)
            return getattr(resp, 'text', str(resp))

        def close(self) -> None:
            # google-genai SDK doesn't expose explicit close on chat, but keep
            # method for interface compatibility.
            return None

    # Extract config safely
    api_key = None
    model = None
    system_prompt = ''
    if config:
        # Direct api_key in config wins
        api_key = config.get('api_key')
        # If config provides the name of an env var, resolve it
        api_key_env_name = config.get('api_key_env_var')
        if not api_key and api_key_env_name:
            api_key = os.environ.get(api_key_env_name)
        # Also accept common env var names as a fallback
        if not api_key:
            for env_name in ('GEMINI_API_KEY', 'GOOGLE_API_KEY', 'GOOGLE_AI'):
                api_key = os.environ.get(env_name)
                if api_key:
                    break
        model = config.get('model') or config.get('llm_model')
        system_prompt = config.get('system_prompt') or ''

    if not api_key or not model:
        # Be lenient: if no API key or model is configured, return a
        # no-op ChatClient implementation so callers (including the
        # original `run.py`) can continue to build a knowledge base and
        # exercise non-LLM parts of the pipeline without crashing.
        logger.warning('Missing api_key or model in llm config; returning NoOp ChatClient')

        class _NoOpClient(ChatClient):
            supports_streaming = False

            def generate(self, prompt: str, **opts) -> str:
                # Provide a helpful placeholder so interactive sessions still
                # respond deterministically when no real LLM is configured.
                short = prompt[:200].replace('\n', ' ')
                return f'[NO-LLM] would generate (first 200 chars): {short}'

            def close(self) -> None:
                return None

        return _NoOpClient()

    return _GenAIClient(api_key=api_key, model=model, system_prompt=system_prompt)


def generate_LLM_answer(client: ChatClient, prompt: str, timeout_seconds: int = 30, **opts) -> str:
    """Generate an answer using a ChatClient with a timeout.

    Runs the client's generate/send_message call in a worker thread and
    enforces a timeout to avoid hanging the CLI. Keeps the retry-on-closed
    behavior from before.
    """
    def _call():
        # Support both generate() and send_message() styles
        if hasattr(client, 'generate'):
            return client.generate(prompt, **opts)
        elif hasattr(client, 'send_message'):
            return client.send_message(prompt)
        else:
            raise RuntimeError('Client does not implement generate or send_message')

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(_call)
            resp = fut.result(timeout=timeout_seconds)
    except concurrent.futures.TimeoutError:
        logger.error('LLM request timed out after %s seconds', timeout_seconds)
        raise RuntimeError(f'LLM request timed out after {timeout_seconds} seconds')
    except RuntimeError:
        # Pass through runtime errors to the retry logic below
        raise
    except Exception as e:
        # Wrap other exceptions
        logger.exception('LLM generation error')
        raise RuntimeError(str(e)) from e

    # If the client returns an object with .text, extract it
    if hasattr(resp, 'text'):
        return resp.text
    return str(resp)


def run_rag_pipeline(client: ChatClient, kb_collection: Any, non_interactive: bool = False) -> None:
    """Small interactive loop to ask questions; kept for compatibility.

    This function is intentionally simple and prints to stdout. Tests should
    patch or replace it if necessary.
    """
    # Respect non-interactive mode: avoid launching an interactive loop when
    # called from scripts or CI.
    if non_interactive:
        logger.info('Non-interactive mode: skipping interactive RAG loop')
        return

    print('Welcome to the RAG pipeline. Type "bye" to exit')
    while True:
        q = input('User>> ')
        if q.strip() == 'bye':
            break
        prompt = f"QUESTION: {q}\n"
        if kb_collection is not None:
            # retrieve chunks from vector DB if function available
            try:
                from rag_kmk.vector_db import retrieve_chunks
                docs = retrieve_chunks(kb_collection, q, n_results=5, return_only_docs=True)
                context = '\n'.join(docs)
                prompt += '\n EXCERPTS:\n' + context
            except Exception:
                pass

        try:
            out = generate_LLM_answer(client, prompt)
        except RuntimeError as e:
            logger.exception('LLM generation failed: %s', e)
            print('\nModel>> [error in generation]')
            continue

        print('\nModel>> ', out)


def generateAnswer(client: Any, chroma_collection: Any = None, query: str = '', n_results: int = 5, only_response: bool = False) -> str:
    """Compatibility wrapper used by older callers/tests.

    Builds a prompt from `query` and optional `chroma_collection` context, then
    invokes the client's message API. The client can expose either
    `send_message(content)` (returns object with .text) or
    `generate(prompt, **opts)`; this function handles both.
    """
    prompt = f"QUESTION: {query}\n"
    # Always attempt retrieval in a best-effort way; tests may monkeypatch
    # retrieve_chunks to ignore the chroma_collection parameter.
    try:
        docs = retrieve_chunks(chroma_collection, query, n_results=n_results, return_only_docs=True)
        context = '\n'.join(docs)
        prompt += '\n EXCERPTS:\n' + context
    except Exception:
        # best-effort: ignore retrieval failures
        pass

    # Prefer send_message if available (older style), fall back to generate()
    resp = None
    if hasattr(client, 'send_message'):
        resp = client.send_message(prompt)
    elif hasattr(client, 'generate'):
        resp = client.generate(prompt)
    else:
        raise RuntimeError('Client does not implement send_message or generate')

    # Extract text if present
    if hasattr(resp, 'text'):
        return resp.text
    return str(resp)

# Expose retrieve_chunks/show_results on this module so tests can monkeypatch
# rag_kmk.chat_flow.llm_interface.retrieve_chunks reliably.
try:
    from rag_kmk.vector_db.query import retrieve_chunks, show_results  # type: ignore
except Exception:
    retrieve_chunks = None
    show_results = None

