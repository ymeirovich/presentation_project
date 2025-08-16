from __future__ import annotations
import json, os, tempfile, pathlib, fcntl
from typing import Dict, Tuple

_STATE = pathlib.Path("out/state/idempotency.json")
_STATE.parent.mkdir(parents=True, exist_ok=True)

def _atomic_write(path: pathlib.Path, data: str) -> None:
    tmp = pathlib.Path(tempfile.mkstemp(prefix="idem_", dir=str(path.parent))[1])
    try:
        tmp.write_text(data, encoding="utf-8")
        os.replace(tmp, path)
    finally:
        try: tmp.unlink(missing_ok=True)
        except Exception: pass

def load_cache() -> Dict[str, Tuple[str, str, str]]:
    if not _STATE.exists():
        return {}
    with _STATE.open("r", encoding="utf-8") as f:
        # lock shared read (best effort; works on Unix)
        try: fcntl.flock(f, fcntl.LOCK_SH)
        except Exception: pass
        data = json.load(f)
    return {k: tuple(v) for k, v in data.items()}  # type: ignore

def save_cache(cache: Dict[str, Tuple[str, str, str]]) -> None:
    payload = json.dumps(cache, ensure_ascii=False)
    _atomic_write(_STATE, payload)
