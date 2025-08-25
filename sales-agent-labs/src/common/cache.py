# src/common/cache.py
from __future__ import annotations
import hashlib, json, os, time, tempfile
from pathlib import Path
from typing import Any, Optional

DEFAULT_STATE_DIR = Path("out/state")


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _ns_dir(namespace: str, root: Path = DEFAULT_STATE_DIR) -> Path:
    p = root / "cache" / namespace
    p.mkdir(parents=True, exist_ok=True)
    return p


def _now() -> float:
    return time.time()


def _is_fresh(path: Path, ttl_secs: Optional[float]) -> bool:
    if ttl_secs is None:
        return True
    if not path.exists():
        return False
    age = _now() - path.stat().st_mtime
    return age <= ttl_secs


def get(
    namespace: str,
    key: str,
    *,
    ttl_secs: Optional[float] = None,
    root: Path = DEFAULT_STATE_DIR,
) -> Optional[dict]:
    """Return JSON object from cache if fresh, else None."""
    path = _ns_dir(namespace, root) / f"{key}.json"
    if not path.exists():
        return None
    if not _is_fresh(path, ttl_secs):
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None  # defensive: corrupt cache shouldn't crash pipeline


def set(namespace: str, key: str, obj: dict, *, root: Path = DEFAULT_STATE_DIR) -> None:
    """Atomically write JSON to cache."""
    dirp = _ns_dir(namespace, root)
    final = dirp / f"{key}.json"
    # atomic write: temp file then rename
    with tempfile.NamedTemporaryFile(
        "w", delete=False, dir=str(dirp), encoding="utf-8"
    ) as tf:
        json.dump(obj, tf, ensure_ascii=False, indent=2)
        tmpname = tf.name
    os.replace(tmpname, final)  # atomic on POSIX


def llm_key(
    report_text: str, max_bullets: int, max_script_chars: int, model: str
) -> str:
    payload = f"llm|{model}|{max_bullets}|{max_script_chars}|{report_text}"
    return _sha256_hex(payload)


def imagen_key(
    prompt: str, aspect: str, size: str, model: str, share_public: bool
) -> str:
    payload = f"img|{model}|{aspect}|{size}|{share_public}|{prompt}"
    return _sha256_hex(payload)
