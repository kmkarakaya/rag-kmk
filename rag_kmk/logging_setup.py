import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional

DEFAULT_LOG_FILE = "logs/rag_kmk.log"
DEFAULT_LEVEL = "INFO"
DEFAULT_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_BACKUP_COUNT = 3


def _parse_cfg(cfg: Optional[dict]):
    logcfg = (cfg or {}).get("logging", {}) if isinstance(cfg, dict) else {}
    return {
        "level": logcfg.get("level", DEFAULT_LEVEL),
        "file": logcfg.get("file", DEFAULT_LOG_FILE),
        "max_bytes": int(logcfg.get("max_bytes", DEFAULT_MAX_BYTES)),
        "backup_count": int(logcfg.get("backup_count", DEFAULT_BACKUP_COUNT)),
    }


def init_logging_from_config(config: Optional[dict] = None, force: bool = False):
    """
    Initialize root logging handlers based on config.
    - If handlers already present and force is False, do nothing and return SKIPPED.
    - Returns dict with status and detail.
    """
    cfg = _parse_cfg(config)
    root = logging.getLogger()
    # If there are already handlers and we are not forcing, skip to be non-invasive
    if root.handlers and not force:
        return {"status": "SKIPPED", "reason": "root logger already has handlers"}

    level = getattr(logging, cfg["level"].upper(), logging.INFO)
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"

    # If forcing, remove existing handlers
    if root.handlers and force:
        for h in list(root.handlers):
            try:
                root.removeHandler(h)
            except Exception:
                pass

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(logging.Formatter(fmt))

    log_file_path = cfg["file"]
    log_dir = os.path.dirname(log_file_path) or "."
    try:
        os.makedirs(log_dir, exist_ok=True)
        fh = RotatingFileHandler(log_file_path, maxBytes=cfg["max_bytes"], backupCount=cfg["backup_count"], encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(logging.Formatter(fmt))
        root.setLevel(level)
        root.addHandler(console)
        root.addHandler(fh)
        return {"status": "OK", "file": log_file_path, "level": cfg["level"]}
    except Exception as e:
        # Fall back to console-only
        root.setLevel(level)
        root.addHandler(console)
        return {"status": "ERROR", "error": str(e)}
