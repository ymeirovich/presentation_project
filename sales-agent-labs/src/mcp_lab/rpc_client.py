from __future__ import annotations
import json, logging, subprocess, sys, threading, queue, time, uuid
from typing import Any, Dict, Optional

log = logging.getLogger("mcp_lab.rpc_client")

class ToolError(RuntimeError):
    """Raised when the MCP server returns an error object."""

class MCPClient:
    """
    Starts your MCP server as a subprocess and speaks JSON-RPC over stdio.
    Keeps one process per client (faster than one-shot processes per call).
    """
    def __init__(self, cmd: Optional[list[str]] = None, start_timeout: float = 5.0):
        self.cmd = cmd or [sys.executable, "-m", "src.mcp.server"]
        self._p: Optional[subprocess.Popen] = None
        self._rx: "queue.Queue[str]" = queue.Queue()
        self._reader_thread: Optional[threading.Thread] = None
        self.start_timeout = start_timeout

    def __enter__(self) -> "MCPClient":
        self._p = subprocess.Popen(
            self.cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
            text=True,
            bufsize=1,
        )
        assert self._p.stdin and self._p.stdout
        self._reader_thread = threading.Thread(target=self._reader, daemon=True)
        self._reader_thread.start()
        # Give server a moment to initialize
        time.sleep(0.2)
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if self._p and self._p.stdin:
                try:
                    self._p.stdin.close()
                except Exception:
                    pass
            if self._p:
                self._p.terminate()
                self._p.wait(timeout=2)
        except Exception:
            if self._p:
                self._p.kill()

    def _reader(self):
        assert self._p and self._p.stdout
        for line in self._p.stdout:
            self._rx.put(line.rstrip("\n"))

    def call(
        self,
        method: str,
        params: Dict[str, Any],
        *,
        req_id: Optional[str] = None,
        timeout: float = 60.0,
    ) -> Dict[str, Any]:
        if not self._p or not self._p.stdin:
            raise RuntimeError("Client not started; use MCPClient() as a context manager")
        rid = req_id or str(uuid.uuid4())
        payload = {"jsonrpc": "2.0", "id": rid, "method": method, "params": params}
        print(json.dumps(payload, ensure_ascii=False), file=self._p.stdin, flush=True)

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                resp_line = self._rx.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                resp = json.loads(resp_line)
            except json.JSONDecodeError:
                continue
            if resp.get("id") != rid:
                continue
            if "error" in resp:
                raise ToolError(resp["error"])
            return resp.get("result", {})
        raise TimeoutError(f"Timed out waiting for response to {method}")
