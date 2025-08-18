# src/common/devdebug.py
from __future__ import annotations
import os

def maybe_listen(default_port: int = 5678) -> None:
    """
    If DEBUGPY=1 is set, start a debugpy server so VS Code can attach.
    If DEBUGPY_WAIT=1 is also set, pause until a client attaches.
    Safe to call multiple times; it won't re-bind the port.
    """
    if os.getenv("DEBUGPY") != "1":
        return
    try:
        import debugpy
    except Exception:
        # Optional: silently ignore if debugpy isn't installed
        return

    # If not already listening, bind
    try:
        debugpy.listen(("0.0.0.0", int(os.getenv("DEBUGPY_PORT", default_port))))
    except RuntimeError:
        # Already listening
        pass

    if os.getenv("DEBUGPY_WAIT") == "1":
        print("[debug] Waiting for VS Code to attach…")
        debugpy.wait_for_client()
        print("[debug] VS Code attached.")

def maybe_break() -> None:
    """
    Drop into a breakpoint if either VS Code is attached
    or user set DEBUGPY_BREAK=1. Works without VS Code too (falls back to pdb).
    """
    import os, builtins
    if os.getenv("DEBUGPY_BREAK") == "1":
        builtins.breakpoint()  # VS Code will catch if attached; otherwise falls to pdb
