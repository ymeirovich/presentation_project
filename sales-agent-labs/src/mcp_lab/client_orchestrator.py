from __future__ import annotations
import json, subprocess, sys, time
from typing import Any, Dict

def _call(method: str, params: dict | None = None, timeout: float = 30.0) -> dict:
    proc = subprocess.Popen(
        [sys.executable, "-m", "src.mcp.server"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1
    )
    try:
        req = {"jsonrpc":"2.0","id":1,"method":method,"params":params or {}}
        assert proc.stdin and proc.stdout
        proc.stdin.write(json.dumps(req) + "\n"); proc.stdin.flush()

        start = time.time()
        while True:
            line = proc.stdout.readline()
            if line:
                return json.loads(line)
            if time.time() - start > timeout:
                raise TimeoutError(f"{method} timed out after {timeout}s")
    finally:
        proc.terminate()
        try: proc.wait(timeout=1)
        except Exception: proc.kill()

def orchestrate(report_text: str) -> Dict[str, Any]:
    s = _call("llm.summarize", {
        "report_text": report_text,
        "max_bullets": 5,
        "max_script_chars": 700
    })
    if "error" in s:
        raise RuntimeError(f"llm.summarize failed: {s['error']}")
    outline = s["result"]

    img = _call("image.generate", {
        "prompt": outline["image_prompt"],
        "aspect": "16:9",
        "return_drive_link": True
    })
    if "error" in img:
        raise RuntimeError(f"image.generate failed: {img['error']}")
    image_url = img["result"].get("url")
    image_local = img["result"].get("local_path")

    slide_params = {
        "client_request_id": f"deck-{int(time.time())}",
        "title": outline["title"],
        "subtitle": outline["subtitle"],
        "bullets": outline["bullets"],
        "script": outline["script"],
    }
    if image_url:
        slide_params["image_url"] = image_url
    elif image_local:
        slide_params["image_local_path"] = image_local

    deck = _call("slides.create", slide_params)
    if "error" in deck:
        raise RuntimeError(f"slides.create failed: {deck['error']}")
    return deck["result"]

if __name__ == "__main__":
    demo_text = (
        "Acme FinTech is modernizing ETL to reduce infra spend and speed insights.\n"
        "Priority: cost reduction, compliance risk, faster analytics.\n"
        "Current stack: fragmented pipelines; goal: consolidation and governance."
    )
    res = orchestrate(demo_text)
    print(json.dumps(res, indent=2))
