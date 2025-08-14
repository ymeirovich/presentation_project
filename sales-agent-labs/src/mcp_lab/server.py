from __future__ import annotations
import logging, sys, traceback
from typing import Any, Callable, Dict

from .protocol import FramedIO
from .schemas import (
    JsonRpcRequest, JsonRpcResponse, JsonRpcErrorObj,
    ReverseStringParams, ReverseStringResult,
    DraftSlideOutlineParams, DraftSlideOutlineResult,
)

log = logging.getLogger("mcp.server")

# ---- Tool registry ----------------------------------------------------------

ToolFn = Callable[[dict], dict]

def tool_reverse_string(params: dict) -> dict:
    p = ReverseStringParams.model_validate(params)
    result = ReverseStringResult(reversed=p.text[::-1])
    return result.model_dump()

def tool_draft_slide_outline(params: dict) -> dict:
    p = DraftSlideOutlineParams.model_validate(params)

    # NOTE: This is a MOCK for Day 10. Later you’ll call Gemini 1.5.
    # Keep logic explainable: extract first line as a title-ish, simple bullets.
    lines = [ln.strip() for ln in p.report_text.splitlines() if ln.strip()]
    title = (lines[0][:90] if lines else "Opportunity Overview")
    subtitle = "Why this matters to the prospect"
    # Cheap heuristic: pick sentences or short lines as bullets
    candidates = []
    for ln in lines[1:]:
        if 3 <= len(ln.split()) <= 18:
            candidates.append(ln)
        if len(candidates) >= p.max_bullets:
            break
    if not candidates:
        candidates = ["Key value driver 1", "Key value driver 2", "Key value driver 3"]

    res = DraftSlideOutlineResult(title=title, subtitle=subtitle, bullets=candidates)
    return res.model_dump()

TOOLS: Dict[str, ToolFn] = {
    "reverse_string": tool_reverse_string,
    "draft_slide_outline": tool_draft_slide_outline,
}

# ---- JSON-RPC dispatch ------------------------------------------------------

def _success(id_: int, result: dict) -> dict:
    return JsonRpcResponse(id=id_, result=result).model_dump()

def _error(id_: int, code: int, message: str, data: dict | None = None) -> dict:
    return JsonRpcResponse(
        id=id_,
        error=JsonRpcErrorObj(code=code, message=message, data=data).model_dump()
    ).model_dump()

def serve_stdio() -> int:
    io = FramedIO(sys.stdin, sys.stdout)
    log.info("MCP-lab server started (NDJSON over stdio).")

    while True:
        msg = io.read_message()
        if msg is None:
            # EOF or blank line; exit gracefully if stdin is closed.
            if sys.stdin.closed:
                break
            continue

        try:
            req = JsonRpcRequest.model_validate(msg)
        except Exception as e:
            # Cannot parse as JSON-RPC request; return protocol error if possible
            # (-32600 Invalid Request)
            io.write_message(_error(id_=msg.get("id", 0), code=-32600, message="Invalid Request"))
            continue

        try:
            if req.method == "ping":
                io.write_message(_success(req.id, {"ok": True}))
                continue

            tool = TOOLS.get(req.method)
            if not tool:
                # -32601 Method not found
                io.write_message(_error(req.id, -32601, f"Unknown tool: {req.method}"))
                continue

            params = req.params or {}
            # Defensive: cap param size to avoid memory blowups
            if len(str(params)) > 200_000:
                io.write_message(_error(req.id, -32001, "params too large"))
                continue

            result = tool(params)  # may raise validation error
            io.write_message(_success(req.id, result))
        except Exception as e:
            # -32000 Server error (include a safe summary; redact internals in production)
            tb = traceback.format_exc(limit=2)
            log.exception("Tool error for %s", req.method)
            io.write_message(_error(req.id, -32000, "Tool execution failed", data={"trace": tb}))

    log.info("Server exiting.")
    return 0

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    raise SystemExit(serve_stdio())
