from __future__ import annotations
import json
import logging
from typing import IO, Optional

log = logging.getLogger("mcp.protocol")

class FramedIO:
    """
    Very simple NDJSON framing: one JSON per line.
    In a production MCP server you’d implement Content-Length framing.
    """
    def __init__(self, reader: IO[str], writer: IO[str]):
        self._r = reader
        self._w = writer

    def read_message(self) -> Optional[dict]:
        line = self._r.readline()
        if not line:
            return None
        line = line.strip()
        if not line:
            return None
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            log.warning("Dropped invalid JSON line (not fatal).")
            return None

    def write_message(self, obj: dict) -> None:
        # Defensive: ensure it’s JSON-serializable
        payload = json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
        self._w.write(payload + "\n")
        self._w.flush()
