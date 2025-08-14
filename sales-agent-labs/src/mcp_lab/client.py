from __future__ import annotations
import json, subprocess, sys, time, os
from typing import Any

def call_server(method: str, params: dict | None = None, timeout: float = 5.0) -> dict:
    """
    Spawns the server as a subprocess and sends one JSON-RPC request over stdin.
    Returns the parsed JSON-RPC response (dict).
    """
    env = os.environ.copy()
    # Reuse your project venv/env; nothing special required here.
    proc = subprocess.Popen(
        [sys.executable, "-m", "src.mcp_lab.server"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1
    )
    try:
        req = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
        proc.stdin.write(json.dumps(req) + "\n")
        proc.stdin.flush()

        # Read one line (one message) back
        start = time.time()
        while True:
            if proc.stdout is None:
                raise RuntimeError("No stdout from server")
            line = proc.stdout.readline()
            if line:
                return json.loads(line)
            if time.time() - start > timeout:
                raise TimeoutError("Server did not respond in time")

    finally:
        # Be sure to terminate the server process
        proc.terminate()
        try:
            proc.wait(timeout=1)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    # Example calls:
    print(call_server("ping"))
    print(call_server("reverse_string", {"text": "hello MCP"}))
    print(call_server("draft_slide_outline", {
        "report_text": "Acme is modernizing ETL. Savings, risk reduction.\nLower infra spend.\nFaster time to insight.",
        "max_bullets": 4
    }))
