# src/mcp_lab/orchestrator.py
from __future__ import annotations

import hashlib
import logging
import time
import uuid
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .rpc_client import MCPClient, ToolError
from src.common.cache import get as cache_get, set as cache_set, llm_key, imagen_key
from src.common.jsonlog import jlog

log = logging.getLogger("orchestrator")


def orchestrate(
    report_text: str,
    *,
    client_request_id: Optional[str] = None,
    slide_count: int = 3,
    use_cache: bool = False,
    cache_ttl_secs: Optional[float] = 36000.0,
    llm_model: str = "models/gemini-2.0-flash-001",
    imagen_model: str = "imagegeneration@006",
    imagen_size: str = "1280x720",
) -> Dict[str, Any]:
    """
    Flow:
      1) llm.summarize -> sections[] (or single slide fields)
      2) For each section up to slide_count (≤ N):
           image.generate (best effort, cached)
           slides.create (first creates deck; rest append via presentation_id)
    """
    req_id = client_request_id or str(uuid.uuid4())

    # ----------------------------
    # 1) LLM summarize (with cache)
    # ----------------------------
    # Cap the hint sensibly (don’t force N, just allow up to N)
    max_sections_hint = max(1, min(10, slide_count))

    # include the hint in the cache key so different requested sizes don’t collide
    llm_cache_key = llm_key(report_text, 5, 700, llm_model) + f":msec={max_sections_hint}"

    def _call_llm() -> Dict[str, Any]:
        with MCPClient() as client:
            s = client.call(
                "llm.summarize",
                {
                    "report_text": report_text,
                    "max_bullets": 5,
                    "max_script_chars": 700,
                    # ✅ correct: “no more than N”, tool may return fewer
                    "max_sections": max_sections_hint,
                },
                req_id=req_id,
            )
            # 🔧 print raw JSON to console for this run
            import json
            print(json.dumps(s, indent=2, ensure_ascii=False))
            return s

    if use_cache:
        cached = cache_get("llm_summarize", llm_cache_key, ttl_secs=cache_ttl_secs)
        if cached:
            jlog(log, logging.INFO, event="cache_hit", layer="llm.summarize", req_id=req_id)
            s = cached
        else:
            s = _call_llm()
            cache_set("llm_summarize", llm_cache_key, s)
            jlog(log, logging.INFO, event="cache_miss_store", layer="llm.summarize", req_id=req_id)
    else:
        s = _call_llm()

    # Normalize to sections[]
    sections = s.get("sections")
    if not isinstance(sections, list):
        sections = [{
            "title": s.get("title") or "Untitled",
            "subtitle": s.get("subtitle"),
            "bullets": s.get("bullets") or [],
            "script": s.get("script") or "",
            "image_prompt": s.get("image_prompt"),
        }]

    jlog(
        log, logging.INFO, event="sections_debug",
        count=len(sections), titles=[(sec.get("title") or "")[:60] for sec in sections]
    )

    # Never fabricate slides; use at most slide_count
    desired = max(1, min(10, slide_count))
    actual = min(desired, len(sections))
    if actual < desired:
        jlog(
            log,
            logging.INFO,
            event="fewer_sections_than_requested",
            requested=desired,
            received=len(sections),
            will_create=actual,
            req_id=req_id,
        )
    if actual == 0:
        return {"presentation_id": None, "url": None, "created_slides": 0, "first_slide_id": None}

    # ---------------------------------
    # 2) For each section (≤ N): build
    # ---------------------------------
    created_pres_id: Optional[str] = None
    deck_url: Optional[str] = None
    first_slide_id: Optional[str] = None

    for idx, sec in enumerate(sections[:actual], start=1):
        per_slide_id = f"{req_id}#s{idx}"

        # 2a) Best-effort image (with cache)
        image_url: Optional[str] = None
        image_drive_file_id: Optional[str] = None
        image_local_path: Optional[str] = None
        image_prompt = sec.get("image_prompt")

        def _imagen_call() -> Dict[str, Any]:
            with MCPClient() as client:
                return client.call(
                    "image.generate",
                    {
                        "prompt": image_prompt,
                        "aspect": "16:9",
                        "size": imagen_size,
                        "safety_tier": "default",
                        "share_public": True,
                    },
                    req_id=per_slide_id,
                )

        if image_prompt:
            try:
                if use_cache:
                    ikey = imagen_key(image_prompt, "16:9", imagen_size, imagen_model, True)
                    icached = cache_get("imagen", ikey, ttl_secs=cache_ttl_secs)
                    if icached and (icached.get("image_url") or icached.get("drive_file_id")):
                        jlog(log, logging.INFO, event="cache_hit", layer="image.generate", req_id=per_slide_id)
                        image_url = icached.get("image_url")
                        image_drive_file_id = icached.get("drive_file_id")
                    else:
                        g = _imagen_call()
                        jlog(log, logging.INFO, event="image_generate_raw", req_id=per_slide_id, result=g)
                        image_url = g.get("image_url") or g.get("url")
                        image_drive_file_id = g.get("drive_file_id")
                        image_local_path = g.get("local_path")
                        cache_set("imagen", ikey, {"image_url": image_url, "drive_file_id": image_drive_file_id})
                        jlog(log, logging.INFO, event="cache_miss_store", layer="image.generate", req_id=per_slide_id)
                else:
                    g = _imagen_call()
                    image_url = g.get("image_url") or g.get("url")
                    image_drive_file_id = g.get("drive_file_id")
                    image_local_path = g.get("local_path")

                if not (image_url or image_drive_file_id or image_local_path):
                    jlog(
                        log, logging.WARNING, event="image_generate_no_usable_fields",
                        req_id=per_slide_id, keys=list(g.keys()) if "g" in locals() else [],
                    )
            except ToolError as e:
                jlog(log, logging.WARNING, event="image_generate_failed", req_id=per_slide_id, err=str(e))

        # 2b) Create or append slide
        slide_params: Dict[str, Any] = {
            "client_request_id": per_slide_id,  # idempotency per slide
            "title": sec.get("title") or "Untitled",
            "subtitle": sec.get("subtitle"),
            "bullets": sec.get("bullets") or [],
            "script": sec.get("script") or "",
            "share_image_public": True,
            "aspect": "16:9",
        }
        if image_url:
            slide_params["image_url"] = image_url
        elif image_drive_file_id:
            slide_params["image_drive_file_id"] = image_drive_file_id
        elif image_local_path:
            slide_params["image_local_path"] = image_local_path

        if created_pres_id:
            slide_params["presentation_id"] = created_pres_id  # append mode

        import json
        print(f"DEBUG: slide_params for slide {idx}: {json.dumps(slide_params, indent=2)}")

        with MCPClient() as client:
            create_res = client.call("slides.create", slide_params, req_id=per_slide_id)

        if idx == 1:
            created_pres_id = create_res.get("presentation_id") or created_pres_id
            deck_url = create_res.get("url") or deck_url
            first_slide_id = create_res.get("slide_id") or first_slide_id

        jlog(
            log, logging.INFO, event="slide_ok",
            req_id=per_slide_id, idx=idx,
            presentation_id=created_pres_id, slide_id=create_res.get("slide_id"),
        )

    jlog(
        log, logging.INFO, event="orchestrate_ok",
        req_id=req_id, presentation_id=created_pres_id, url=deck_url, created_slides=actual,
    )

    return {
        "presentation_id": created_pres_id,
        "url": deck_url,
        "created_slides": actual,
        "first_slide_id": first_slide_id,
    }


def _stable_request_id(report_text: str) -> str:
    h = hashlib.sha256(report_text.encode("utf-8")).hexdigest()[:16]
    return f"req-{h}"


def orchestrate_many(
    items: Iterable[Tuple[str, str]],
    *,
    sleep_between_secs: float = 0.0,
    slide_count: int = 1,
) -> List[Dict[str, Any]]:
    item_list: List[Tuple[str, str]] = list(items)

    results: List[Dict[str, Any]] = []
    for idx, (name, text) in enumerate(item_list, start=1):
        req_id = _stable_request_id(text)
        jlog(log, logging.INFO, event="batch_item_start", idx=idx, name=name, req_id=req_id)
        try:
            res = orchestrate(text, client_request_id=req_id, slide_count=slide_count)
            results.append({
                "name": name,
                "request_id": req_id,
                "presentation_id": res.get("presentation_id"),
                "url": res.get("url"),
                "created_slides": res.get("created_slides"),
                "ok": True,
                "error": None,
            })
            jlog(log, logging.INFO, event="batch_item_ok", idx=idx, name=name, req_id=req_id, url=res.get("url"))
        except Exception as e:
            results.append({
                "name": name,
                "request_id": req_id,
                "presentation_id": None,
                "url": None,
                "created_slides": 0,
                "ok": False,
                "error": str(e),
            })
            jlog(log, logging.ERROR, event="batch_item_fail", idx=idx, name=name, req_id=req_id, err=str(e))

        if sleep_between_secs > 0 and idx < len(item_list):
            time.sleep(sleep_between_secs)

    ok_count = sum(1 for r in results if r["ok"])
    jlog(log, logging.INFO, event="batch_summary", total=len(item_list), ok=ok_count, fail=len(results) - ok_count)
    return results
