from __future__ import annotations
from .rpc_client import MCPClient, ToolError
from src.common.jsonlog import jlog

import logging, uuid, time, hashlib, pathlib
from typing import Any, Dict, Iterable, List, Optional, Tuple

log = logging.getLogger("orchestrator")

def orchestrate(report_text: str, *, client_request_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Flow:
      1) llm.summarize → {title, subtitle, bullets[], script, image_prompt}
      2) image.generate (best-effort) → image_url | None
      3) slides.create (idempotent if client_request_id given) → {presentation_id, slide_id, url}
    """
    req_id = client_request_id or str(uuid.uuid4())

    with MCPClient() as client:
        # 1) Summarize
        s = client.call("llm.summarize", {
            "report_text": report_text,
            "max_bullets": 5,
            "max_script_chars": 700,
        }, req_id=req_id)

        title = s["title"]
        subtitle = s["subtitle"]
        bullets = s["bullets"]
        script = s["script"]
        image_prompt = s["image_prompt"]

        # 2) Generate image (soft dependency)
        image_url: Optional[str] = None
        try:
            g = client.call("image.generate", {
                "prompt": image_prompt,
                "aspect": "16:9",
                "share_public": True
            }, req_id=req_id)
            image_url = g.get("image_url")
        except ToolError as e:
            jlog(log, logging.WARNING, event="image_generate_failed", req_id=req_id, err=str(e))

        # 3) Create slide (idempotent)
        create = client.call("slides.create", {
            "client_request_id": req_id,
            "title": title,
            "subtitle": subtitle,
            "bullets": bullets,
            "script": script,
            # choose exactly one of image_local_path / image_url / image_drive_file_id
            "image_url": image_url,
            "share_image_public": True,
            "aspect": "16:9",
        }, req_id=req_id)

        jlog(log, logging.INFO, event="orchestrate_ok", req_id=req_id,
             presentation_id=create.get("presentation_id"),
             slide_id=create.get("slide_id"),
             url=create.get("url"))

        return create


def _stable_request_id(report_text: str) -> str:
    """Deterministic idempotency key for the same content (ok for Day 13)."""
    h = hashlib.sha256(report_text.encode("utf-8")).hexdigest()[:16]
    return f"req-{h}"

def orchestrate_many(
    items: Iterable[Tuple[str, str]],  # (report_name, report_text)
    *,
    sleep_between_secs: float = 0.0,
) -> List[Dict[str, Any]]:
    """
    Sequentially process a list of reports.
    Returns a list of results: [{name, presentation_id, slide_id, url, request_id, ok, error}]
    """
    results: List[Dict[str, Any]] = []
    for idx, (name, text) in enumerate(items, start=1):
        req_id = _stable_request_id(text)
        jlog(log, logging.INFO, event="batch_item_start", idx=idx, name=name, req_id=req_id)
        try:
            res = orchestrate(text, client_request_id=req_id)
            results.append({
                "name": name,
                "request_id": req_id,
                "presentation_id": res.get("presentation_id"),
                "slide_id": res.get("slide_id"),
                "url": res.get("url"),
                "ok": True,
                "error": None,
            })
            jlog(log, logging.INFO, event="batch_item_ok", idx=idx, name=name, req_id=req_id, url=res.get("url"))
        except Exception as e:
            results.append({
                "name": name,
                "request_id": req_id,
                "presentation_id": None,
                "slide_id": None,
                "url": None,
                "ok": False,
                "error": str(e),
            })
            jlog(log, logging.ERROR, event="batch_item_fail", idx=idx, name=name, req_id=req_id, err=str(e))
        if sleep_between_secs > 0 and idx < len(list(items)):
            time.sleep(sleep_between_secs)
    # Summary log
    ok_count = sum(1 for r in results if r["ok"])
    jlog(log, logging.INFO, event="batch_summary", total=len(results), ok=ok_count, fail=len(results)-ok_count)
    return results