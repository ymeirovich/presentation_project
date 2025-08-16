from __future__ import annotations
import logging, uuid
from typing import Any, Dict, Optional

from .rpc_client import MCPClient, ToolError
from src.common.jsonlog import jlog

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
