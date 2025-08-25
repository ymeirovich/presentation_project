# tests/test_cache_unit.py
import time
from pathlib import Path
from src.common.cache import (
    get as cget,
    set as cset,
    llm_key,
    imagen_key,
    DEFAULT_STATE_DIR,
)


def test_llm_key_stability():
    k1 = llm_key("hello", 5, 700, "models/gemini-2.0-flash-001")
    k2 = llm_key("hello", 5, 700, "models/gemini-2.0-flash-001")
    assert k1 == k2
    k3 = llm_key("hello!", 5, 700, "models/gemini-2.0-flash-001")
    assert k1 != k3


def test_ttl_behavior(tmp_path: Path):
    # Redirect cache root to temp dir
    root = tmp_path
    payload = {"x": 1}
    cset("unit", "abc", payload, root=root)
    assert cget("unit", "abc", ttl_secs=999, root=root) == payload
    # Make file old by changing mtime
    p = root / "cache" / "unit" / "abc.json"
    old = time.time() - 10
    p.touch()
    ns = p.stat()
    # On some systems we cannot easily set mtime without os.utime; do that:
    import os

    os.utime(p, (old, old))
    assert cget("unit", "abc", ttl_secs=1, root=root) is None
