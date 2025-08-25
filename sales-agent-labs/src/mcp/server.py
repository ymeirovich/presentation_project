# src/mcp/server.py
from __future__ import annotations

import json
import sys
import logging
from typing import Any, Dict
from src.mcp.tools.data import data_query_tool


log = logging.getLogger("mcp.server")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

# --- Tool registry (allowlist) ------------------------------------------------
TOOLS: Dict[str, Any] = {}

# Import and register tools (keep imports after TOOLS is defined)
try:
    from .tools.llm import llm_summarize_tool
    from .tools.imagen import image_generate_tool
    from .tools.slides import slides_create_tool

    TOOLS.update(
        {
            "llm.summarize": llm_summarize_tool,
            "image.generate": image_generate_tool,
            "slides.create": slides_create_tool,
            "data.query": data_query_tool,
        }
    )
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
    Persistent stdio server:
    - Reads JSON lines from stdin in a loop
    - Dispatches each to a tool
    - Writes JSON responses to stdout
    - Continues until stdin is closed or EOF
    """
    import os
    # Set flag to redirect logging setup output to stderr
    os.environ["MCP_SERVER_MODE"] = "true"
    
    log.info("MCP server starting, listening on stdin...")
    
    try:
        while True:
            line = sys.stdin.readline()
            if not line:  # EOF - client disconnected
                log.info("MCP server received EOF, shutting down")
                break
                
            line = line.strip()
            if not line:  # Empty line, skip
                continue
                
            try:
                req = json.loads(line)
            except json.JSONDecodeError as e:
                log.warning("Invalid JSON received: %s", e)
                sys.stdout.write(json.dumps(_error(None, -32700, "Invalid JSON")) + "\n")
                sys.stdout.flush()
                continue

            resp = _handle_request(req)
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
            log.debug("Sent response for method: %s", req.get("method"))
            
    except KeyboardInterrupt:
        log.info("MCP server interrupted")
    except Exception as e:
        log.error("MCP server error: %s", e)
        return 1
        
    log.info("MCP server shutting down")
    return 0


if __name__ == "__main__":
    raise SystemExit(serve_stdio())
