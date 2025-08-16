from __future__ import annotations
import json, logging, time, uuid
from typing import Any

def jlog(logger: logging.Logger, level: int, **kv: Any) -> None:
    kv.setdefault("ts_ms", int(time.time() * 1000))
    kv.setdefault("level", logging.getLevelName(level))
    if "req_id" not in kv:
        kv["req_id"] = str(uuid.uuid4())  # caller can override; useful for tracing
    logger.log(level, json.dumps(kv, ensure_ascii=False))
