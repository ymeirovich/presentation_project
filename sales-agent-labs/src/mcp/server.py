# src/mcp/server.py
from __future__ import annotations

import json
import sys
import logging
from typing import Any, Dict
from src.mcp.tools.data import data_query_tool
import base64
from pathlib import Path


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


# --- JSON encoder for handling bytes objects ---------------------------------
class SafeJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that safely handles bytes and Path objects."""
    
    def default(self, obj):
        if isinstance(obj, bytes):
            # Convert bytes to base64 string with a type hint
            return {
                "__bytes__": base64.b64encode(obj).decode('ascii'),
                "__type__": "bytes"
            }
        elif isinstance(obj, Path):
            # Convert Path objects to strings
            return str(obj)
        elif hasattr(obj, '__dict__'):
            # Handle other complex objects by converting to dict
            try:
                return obj.__dict__
            except (TypeError, AttributeError):
                return str(obj)
        # Let the base class handle other types
        return super().default(obj)


def safe_json_dumps(obj: Any) -> str:
    """Safely serialize objects to JSON, handling bytes and other non-serializable types."""
    return json.dumps(obj, cls=SafeJSONEncoder, ensure_ascii=False)


# --- JSON-RPC helpers ---------------------------------------------------------
def _error(id_: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}


def _success(id_: Any, result: Any) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def _contains_bytes(obj, path=""):
    """Recursively check if an object contains bytes, returning the path if found."""
    if isinstance(obj, bytes):
        return f"{path}[bytes:{len(obj)}]"
    elif isinstance(obj, dict):
        for k, v in obj.items():
            result = _contains_bytes(v, f"{path}.{k}")
            if result:
                return result
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            result = _contains_bytes(v, f"{path}[{i}]")
            if result:
                return result
    return None


def _handle_request(req: Dict[str, Any]) -> Dict[str, Any]:
    id_ = req.get("id")
    method = req.get("method")
    params = req.get("params", {}) or {}

    if not method or method not in TOOLS:
        return _error(id_, -32601, f"Method not found: {method}")

    tool_fn = TOOLS[method]
    try:
        result = tool_fn(params)
        
        # Check for bytes objects in the result before serializing
        bytes_path = _contains_bytes(result)
        if bytes_path:
            log.error("Tool '%s' returned bytes object at path: %s", method, bytes_path)
            log.error("Result keys: %s", list(result.keys()) if isinstance(result, dict) else type(result))
        
        return _success(id_, result)
    except Exception as e:
        # Don't leak stack traces to clients; log server-side.
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
                sys.stdout.write(safe_json_dumps(_error(None, -32700, "Invalid JSON")) + "\n")
                sys.stdout.flush()
                continue

            resp = _handle_request(req)
            try:
                # Check for problematic objects before serialization
                bytes_path = _contains_bytes(resp)
                if bytes_path:
                    log.error("Response contains bytes at: %s, method: %s", bytes_path, req.get("method"))
                
                # Use safe JSON serialization to handle bytes objects
                response_json = safe_json_dumps(resp)
                sys.stdout.write(response_json + "\n")
                sys.stdout.flush()
            except Exception as json_err:
                log.error("Failed to serialize response: %s, resp keys: %s", 
                         json_err, list(resp.keys()) if isinstance(resp, dict) else type(resp))
                # Additional debug info
                if isinstance(resp, dict) and 'result' in resp:
                    result = resp['result']
                    log.error("Result type: %s, result keys: %s", 
                             type(result), list(result.keys()) if isinstance(result, dict) else 'N/A')
                # Send a safe error response
                error_resp = _error(req.get("id"), -32000, f"Response serialization failed: {json_err}")
                sys.stdout.write(json.dumps(error_resp) + "\n")
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
