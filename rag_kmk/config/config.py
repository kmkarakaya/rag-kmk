import os
import yaml
import logging

log = logging.getLogger(__name__)

CONFIG = None


def _normalize_vector_db_config(cfg: dict) -> dict:
    """
    Ensure vector_db uses 'chromaDB_path' and canonical folder name 'chromaDB'.
    Accept legacy key 'chroma_db' and legacy path fragments 'chroma_db'.
    """
    v = cfg.get("vector_db", {}) or {}

    # Support legacy key name 'chroma_db' -> 'chromaDB_path'
    if "chroma_db" in v and "chromaDB_path" not in v:
        # map legacy key to canonical config key
        v["chromaDB_path"] = v.pop("chroma_db")

    # If someone used 'chromaDB_path' with legacy folder fragment, normalize it
    path = v.get("chromaDB_path")
    if isinstance(path, str) and "chroma_db" in path:
        v["chromaDB_path"] = path.replace("chroma_db", "chromaDB")

    cfg["vector_db"] = v
    return cfg


def load_config(config_path: str = None) -> dict:
    """
    Initialize the RAG system with either the default or a custom config.
    If the specified config file does not exist, return an empty config.
    """
    path = config_path or os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(path, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}

    # Normalize vector_db and other legacy fields
    cfg = _normalize_vector_db_config(cfg)

    global CONFIG
    CONFIG = cfg
    return cfg


def mask_config(config: dict, keys: tuple = ('api_key', 'api_key_env_var')) -> dict:
    """Return a shallow copy of config with sensitive keys masked.

    This is a helper for logging or printing configs without leaking secrets.
    """
    import copy
    c = copy.deepcopy(config or {})
    def mask_obj(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if any(s in k.lower() for s in keys):
                    obj[k] = '****'
                else:
                    mask_obj(v)

    mask_obj(c)
    return c