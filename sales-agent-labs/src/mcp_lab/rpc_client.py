from __future__ import annotations
import json, logging, subprocess, sys, threading, queue, time, uuid
from typing import Any, Dict, Optional

log = logging.getLogger("mcp_lab.rpc_client")
DEFAULT_TIMEOUT_SECS = 180
METHOD_TIMEOUTS = {
    "llm.summarize": 120,
    "image.generate": 180,
    "slides.create": 300,  # Reduced from 600s (10min) to 300s (5min)
    "data.query": 180,  # Reduced from 300s (5min) to 180s (3min)
}


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

    def _start(self):
        """Start the MCP server subprocess and reader thread."""
        import os
        import signal
        
        # Clean up any existing process more aggressively
        if self._p:
            try:
                if self._p.poll() is None:  # Process still running
                    self._p.terminate()
                    try:
                        self._p.wait(timeout=3.0)
                    except subprocess.TimeoutExpired:
                        # Force kill if terminate didn't work
                        try:
                            os.kill(self._p.pid, signal.SIGKILL)
                            self._p.wait(timeout=1.0)
                        except (ProcessLookupError, subprocess.TimeoutExpired):
                            pass
            except (ProcessLookupError, AttributeError):
                pass
            finally:
                # Close any open file handles
                for attr in ['stdin', 'stdout', 'stderr']:
                    pipe = getattr(self._p, attr, None)
                    if pipe:
                        try:
                            pipe.close()
                        except:
                            pass
                self._p = None
        
        try:
            # Start new subprocess with better error handling
            self._p = subprocess.Popen(
                self.cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,  # Capture stderr to avoid broken pipe messages
                text=True,
                bufsize=0,  # Unbuffered for more responsive communication
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None,  # Create new process group
            )
            
            # Verify pipes are working
            if not (self._p.stdin and self._p.stdout):
                raise RuntimeError("Failed to create subprocess pipes")
                
            # Start reader thread
            self._reader_thread = threading.Thread(target=self._reader, daemon=True)
            self._reader_thread.start()
            
            # Give server more time to initialize and test communication
            time.sleep(0.5)
            
            # Test that subprocess is still alive
            if self._p.poll() is not None:
                raise RuntimeError(f"MCP server exited immediately with code {self._p.returncode}")
                
            log.info("MCP server started successfully (PID: %d)", self._p.pid)
            
        except Exception as e:
            log.error("Failed to start MCP server: %s", str(e))
            # Clean up on failure
            if self._p:
                try:
                    self._p.terminate()
                except:
                    pass
                self._p = None
            raise RuntimeError(f"Could not start MCP server: {e}")

    def __enter__(self) -> "MCPClient":
        self._start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean shutdown of MCP client and subprocess."""
        import os
        import signal
        
        try:
            # Close stdin first to signal shutdown
            if self._p and self._p.stdin:
                try:
                    self._p.stdin.close()
                except (BrokenPipeError, OSError):
                    pass  # Expected during shutdown
            
            # Terminate subprocess gracefully
            if self._p:
                try:
                    if self._p.poll() is None:  # Still running
                        self._p.terminate()
                        try:
                            self._p.wait(timeout=3.0)
                        except subprocess.TimeoutExpired:
                            # Force kill if needed
                            try:
                                os.kill(self._p.pid, signal.SIGKILL)
                                self._p.wait(timeout=1.0)
                            except (ProcessLookupError, subprocess.TimeoutExpired):
                                pass
                except (ProcessLookupError, AttributeError):
                    pass
                finally:
                    # Close remaining pipes
                    for attr in ['stdout', 'stderr']:
                        pipe = getattr(self._p, attr, None)
                        if pipe:
                            try:
                                pipe.close()
                            except:
                                pass
                    self._p = None
                    
        except Exception as e:
            log.warning("Error during MCPClient cleanup: %s", str(e))

    def _reader(self):
        assert self._p and self._p.stdout
        try:
            for line in self._p.stdout:
                line = line.rstrip("\n")
                if line:  # Ignore empty lines
                    self._rx.put(line)
        except (ValueError, OSError) as e:
            # stdout was closed or subprocess died
            log.warning("Reader thread stopped: %s", e)

    def _ensure_alive(self):
        if self._p is None or self._p.poll() is not None:
            # (re)start the server process
            self._start()

    def call(
        self,
        method: str,
        params: Dict[str, Any],
        *,
        req_id: Optional[str] = None,
        timeout: Optional[float] = None,  # <-- make it Optional
    ) -> Dict[str, Any]:
        if not self._p or not self._p.stdin:
            raise RuntimeError(
                "Client not started; use MCPClient() as a context manager"
            )

        # Resolve timeout here (now that we *have* `method`)
        timeout = (
            timeout
            if timeout is not None
            else METHOD_TIMEOUTS.get(method, DEFAULT_TIMEOUT_SECS)
        )

        rid = req_id or str(uuid.uuid4())
        payload = {"jsonrpc": "2.0", "id": rid, "method": method, "params": params}
        try:
            print(
                json.dumps(payload, ensure_ascii=False), file=self._p.stdin, flush=True
            )
        except (BrokenPipeError, ValueError) as e:  # ValueError: I/O on closed file
            # server likely crashed; restart then retry ONCE
            log.warning("MCP subprocess communication failed (%s), restarting...", e)
            self._ensure_alive()
            print(
                json.dumps(payload, ensure_ascii=False), file=self._p.stdin, flush=True
            )

        deadline = time.time() + timeout
        start_time = time.time()
        last_progress_log = start_time
        
        while time.time() < deadline:
            try:
                resp_line = self._rx.get(timeout=0.5)
            except queue.Empty:
                # Check if subprocess is still alive
                if self._p and self._p.poll() is not None:
                    log.error("MCP subprocess died during %s call (exit code: %s)", 
                             method, self._p.returncode)
                    raise RuntimeError(f"MCP subprocess died during {method} call")
                
                # Log progress every 30 seconds for long operations
                current_time = time.time()
                if current_time - last_progress_log >= 30:
                    elapsed = current_time - start_time
                    remaining = deadline - current_time
                    log.info("Still waiting for %s response (elapsed: %.1fs, remaining: %.1fs)", 
                            method, elapsed, remaining)
                    last_progress_log = current_time
                continue
            
            try:
                resp = json.loads(resp_line)
            except json.JSONDecodeError as e:
                log.warning("Invalid JSON from MCP server: %s (line: %s)", e, resp_line[:100])
                continue
                
            if resp.get("id") != rid:
                log.debug("Ignoring response for different request ID: %s (expected: %s)", 
                         resp.get("id"), rid)
                continue
                
            if "error" in resp:
                raise ToolError(resp["error"])
            return resp.get("result", {})
        
        total_elapsed = time.time() - start_time
        raise TimeoutError(f"Timed out waiting for response to {method} after {total_elapsed:.1f}s (timeout: {timeout}s)")
