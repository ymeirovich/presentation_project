# src/mcp/tools/llm.py
from __future__ import annotations
import json
import logging
import os
import time
from typing import Any, Dict

from pydantic import ValidationError
from vertexai import init as vertex_init
from vertexai.generative_models import GenerativeModel, GenerationConfig
from googleapiclient.errors import HttpError

from ..schemas import SummarizeParams, SummarizeResult
from src.common.config import cfg
from src.common.jsonlog import jlog

log = logging.getLogger("mcp.tools.llm")

SYSTEM_INSTRUCTIONS = (
    "You are a sales enablement assistant. Read the prospect research and produce "
    "a crisp one-slide summary with: title, subtitle, 3-8 bullets (concise), a "
    "75-second presenter script (<= {max_script_chars} chars), and an image_prompt "
    "suitable for a modern, professional illustration. Return JSON only."
)

def _coerce_to_object(data: Any) -> Dict[str, Any]:
    """
    The model sometimes returns a list of one object.
    Accept:  { ... }                     -> return as-is
             [ { ... } ]                 -> unwrap first
    Reject:  anything else               -> raise
    """
    if isinstance(data, dict):
        return data
    if isinstance(data, list) and data and isinstance(data[0], dict):
        log.debug("Model returned a list; unwrapping the first object.")
        return data[0]
    raise RuntimeError(f"Expected a JSON object, got: {type(data).__name__}")

def _call_gemini_once(p: SummarizeParams) -> Dict[str, Any]:
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    region = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
    if not project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT is not set")

    vertex_init(project=project, location=region)

    model_name = cfg("llm", "model", default="models/gemini-2.0-flash-001")
    temperature = cfg("llm", "temperature", default=0.2)
    max_tokens = cfg("llm", "max_output_tokens", default=1024)

    model = GenerativeModel(model_name)

    # Strong JSON-only, single-object prompt, with a tiny example.
    prompt = (
        "Return ONLY a SINGLE JSON object (not an array). No backticks or commentary.\n"
        "Required fields and types:\n"
        "  title: string\n"
        "  subtitle: string\n"
        "  bullets: array of 3-8 short strings\n"
        f"  script: string (<= {p.max_script_chars} chars)\n"
        "  image_prompt: string for a professional, modern illustration\n\n"
        "Example (structure only; adapt content to the research):\n"
        '{\n'
        '  "title": "Acme FinTech — Modernize ETL to Cut Spend",\n'
        '  "subtitle": "Faster insights, lower risk",\n'
        '  "bullets": ["Cut infra costs 20–30%", "Unify pipelines", "Improve governance"],\n'
        '  "script": "Short spoken paragraph...",\n'
        '  "image_prompt": "Professional, minimal illustration of a data pipeline dashboard..." \n'
        '}\n\n'
        "Research:\n"
        f"{p.report_text}\n"
    )

    gen_cfg = GenerationConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
        response_mime_type="application/json",
    )

    resp = model.generate_content(contents=[prompt], generation_config=gen_cfg)
    text = (resp.text or "").strip()

    # Guard: strip accidental ```json fences
    if text.startswith("```"):
        text = text.strip("` \n")
        if text.lower().startswith("json"):
            text = text[4:].lstrip()

    try:
        raw = json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Gemini returned non-JSON: {text[:200]}...") from e

    return _coerce_to_object(raw)

def _retry_json_validate(p: SummarizeParams, attempts: int = 3, base: float = 0.6) -> SummarizeResult:
    last_err: Exception | None = None
    for i in range(attempts):
        try:
            raw = _call_gemini_once(p)
            res = SummarizeResult.model_validate(raw)
            if len(res.script) > p.max_script_chars:
                res.script = res.script[: p.max_script_chars].rstrip()
            jlog(log, logging.INFO, tool="llm.summarize", event="ok", attempt=i + 1)
            return res
        except (ValidationError, RuntimeError, HttpError) as e:
            last_err = e
            delay = base * (2**i)
            jlog(log, logging.WARNING, tool="llm.summarize", event="retry",
                 attempt=i + 1, delay_s=delay, err=type(e).__name__)
            time.sleep(delay)

    assert last_err is not None
    raise RuntimeError(f"LLM structured output failed after {attempts} attempts: {type(last_err).__name__}: {last_err}")

def llm_summarize_tool(params: dict) -> dict:
    p = SummarizeParams.model_validate(params)
    res = _retry_json_validate(p)
    return res.model_dump()
