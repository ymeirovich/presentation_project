from __future__ import annotations
from .rpc_client import MCPClient, ToolError
from src.common.jsonlog import jlog
from src.common.cache import get as cache_get, set as cache_set, llm_key, imagen_key
import logging, uuid, time, hashlib, pathlib
from typing import Any, Dict, Iterable, List, Optional, Tuple

log = logging.getLogger("orchestrator")

def orchestrate(report_text: str, *, 
                client_request_id: Optional[str] = None, 
                use_cache: bool=True,
                cache_ttl_secs: Optional[float] = 36000.0, #default 1 hour; tune via CLI
                llm_model: str= "models/gemini-2.0-flash-001", # helps build cache key
                imagen_model: str= "imagegeneration@006",
                imagen_size: str = "1280x720"
               ) -> Dict[str, Any]:
    """
    Flow:
      1) llm.summarize → {title, subtitle, bullets[], script, image_prompt}
      2) image.generate (best-effort) → image_url | None
      3) slides.create (idempotent if client_request_id given) → {presentation_id, slide_id, url}
    """
    req_id = client_request_id or str(uuid.uuid4())
    # --- LLM (with cache) ---
    s: Dict[str,Any]
    if use_cache:
        k = llm_key(report_text, 5, 700, llm_model)
        cached = cache_get("llm_summarize", k, ttl_secs=cache_ttl_secs)
        if cached:
            jlog(log, logging.INFO, event="cache_hit", layer="llm.summarize", req_id=req_id)
            s = cached
        else:
            with MCPClient() as client:
            # 1) Summarize
                s = client.call("llm.summarize", {
                    "report_text": report_text,
                    "max_bullets": 5,
                    "max_script_chars": 700,
                }, req_id=req_id)
                cache_set("llm_summarize", k, s)
                jlog(log, logging.INFO, event="cache_miss_store", layer="llm.summarize", req_id=req_id)             
    else:
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
        # ---- Imagen (with cache, soft dependency) ----

    image_url: Optional[str] = None
    image_drive_file_id: Optional[str] = None

    if image_prompt:
        try:
            if use_cache:
                ikey = imagen_key(image_prompt, "16:9", imagen_size, imagen_model, True)
                icached = cache_get("image", ikey, ttl_secs=cache_ttl_secs)
                if icached and icached.get("image_url"):
                    jlog(log, logging.INFO, event="cache_hit", layer="image.generate", req_id=req_id)
                    image_url = icached["image_url"]
                else:
                    with MCPClient() as client:
                        g = client.call("image.generate", {
                        "prompt": image_prompt,
                        "aspect": "16:9",
                        "size": "1280x720",
                        # IMPORTANT: choose a schema-allowed tier at the call site
                        # "default" maps to a provider-safe setting in the tool
                        "safety_tier": "default",
                        "share_public": True
                    }, req_id=req_id)
                        # Log exactly what we got back
                    jlog(log, logging.INFO, event="image_generate_raw", req_id=req_id, result=g)
                    # Accept multiple possible result shapes from the tool
                    # Prefer direct URL; fall back to Drive file id.
                    image_url = (
                        g.get("image_url") or   # legacy key
                        g.get("url")            # current key in your Imagen tool
                    )
                    image_drive_file_id = g.get("drive_file_id") or None
                    # If we only have a local path, let the Slides tool upload it (image_local_path path)
                    image_local_path = None
                    if not image_url and g.get("drive_file_id"):
                        fid = g["drive_file_id"]
                        image_url = f"https://drive.google.com/uc?export=download&id={fid}"

                    if (not image_url) and (not image_drive_file_id):
                        image_local_path = g.get("local_path")

                    if not (image_url or image_drive_file_id or image_local_path):
                        jlog(log, logging.WARNING, event="image_generate_no_usable_fields",
                            req_id=req_id, keys=list(g.keys()))
                    cache_set("imagen", ikey, {"image_url": image_url})
                    jlog(log, logging.INFO, event="cache_miss_store", layer="image.generate", req_id=req_id)
            else:   
                with MCPClient() as client:
                    g = client.call("image.generate", {
                    "prompt": image_prompt,
                    "aspect": "16:9",
                    "size": "1280x720",
                    # IMPORTANT: choose a schema-allowed tier at the call site
                    # "default" maps to a provider-safe setting in the tool
                    "safety_tier": "default",
                    "share_public": True
                }, req_id=req_id)
                    # Accept multiple possible result shapes from the tool
                    # Prefer direct URL; fall back to Drive file id.
                    image_url = (
                        g.get("image_url") or   # legacy key
                        g.get("url")            # current key in your Imagen tool
                    )
                    if not image_url and g.get("drive_file_id"):
                        fid = g["drive_file_id"]
                        image_url = f"https://drive.google.com/uc?export=download&id={fid}"

                    if not image_url:
                        jlog(log, logging.WARNING, event="image_generate_no_url", req_id=req_id, result_keys=list(g.keys()))
                    else:
                        jlog(log, logging.INFO, event="image_generate_ok", req_id=req_id, image_url=image_url)

        except ToolError as e:
            jlog(log, logging.WARNING, event="image_generate_failed", req_id=req_id, err=str(e))

        # 3) Create slide (idempotent)
    with MCPClient() as client:
        create = client.call("slides.create", {
            "client_request_id": req_id,
            "title": title,
            "subtitle": subtitle,
            "bullets": bullets,
            "script": script,
            # choose exactly one of image_local_path / image_url / image_drive_file_id
            "image_drive_file_id": image_drive_file_id if image_drive_file_id else None,
            "image_url": image_url,
            "image_local_path": image_local_path if (image_local_path and not image_url and not image_drive_file_id) else None,
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



