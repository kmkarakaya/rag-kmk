"""Small utility helpers for rag_kmk."""
import hashlib
import datetime
import os


def compute_fingerprint(path: str) -> str:
    """Compute a sha256 hex fingerprint for a file at `path`.

    Returns the hex digest as a string. If the file is missing, raises
    FileNotFoundError.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def now_isoutc() -> str:
    """Return current UTC time as ISO8601 string without microseconds."""
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'
