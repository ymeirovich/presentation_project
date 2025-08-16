# src/mcp/server.py
from __future__ import annotations

import json
import sys
import logging
from typing import Any, Dict

log = logging.getLogger("mcp.server")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# --- Tool registry (allowlist) ------------------------------------------------
TOOLS: Dict[str, Any] = {}

# Import and register tools (keep imports after TOOLS is defined)
try:
    from .tools.llm import llm_summarize_tool
    from .tools.imagen import image_generate_tool
    from .tools.slides import slides_create_tool

    TOOLS.update({
        "llm.summarize": llm_summarize_tool,
        "image.generate": image_generate_tool,
        "slides.create":  slides_create_tool,
    })
except Exception as e:
    # Import errors will be visible in tests; keep server importable even if a tool fails to import.
    log.warning("Tool imports failed: %s", e)


# --- JSON-RPC helpers ---------------------------------------------------------
def _error(id_: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}

def _success(id_: Any, result: Any) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": id_, "result": result}

def _handle_request(req: Dict[str, Any]) -> Dict[str, Any]:
    id_ = req.get("id")
    method = req.get("method")
    params = req.get("params", {}) or {}

    if not method or method not in TOOLS:
        return _error(id_, -32601, f"Method not found: {method}")

    tool_fn = TOOLS[method]
    try:
        result = tool_fn(params)
        return _success(id_, result)
    except Exception as e:
        # Don’t leak stack traces to clients; log server-side.
        log.exception("Tool '%s' failed", method)
        return _error(id_, -32000, f"{type(e).__name__}: {e}")

def serve_stdio() -> int:
    """
    Minimal single-request stdio server:
    - Reads one JSON line from stdin
    - Dispatches to a tool
    - Writes one JSON line to stdout
    """
    line = sys.stdin.readline()
    if not line:
        sys.stdout.write(json.dumps(_error(None, -32700, "Empty request")) + "\n")
        sys.stdout.flush()
        return 1
    try:
        req = json.loads(line)
    except json.JSONDecodeError:
        sys.stdout.write(json.dumps(_error(None, -32700, "Invalid JSON")) + "\n")
        sys.stdout.flush()
        return 1

    resp = _handle_request(req)
    sys.stdout.write(json.dumps(resp) + "\n")
    sys.stdout.flush()
    return 0

if __name__ == "__main__":
    raise SystemExit(serve_stdio())
