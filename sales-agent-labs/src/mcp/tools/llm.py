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
from src.agent.prompts import MULTI_SLIDE_SYSTEM_PROMPT

log = logging.getLogger("mcp.tools.llm")

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
    max_tokens = cfg("llm", "max_output_tokens", default=2048)

    model = GenerativeModel(model_name)

    system_prompt = MULTI_SLIDE_SYSTEM_PROMPT.format(
        max_sections=p.max_sections, 
        max_script_chars=p.max_script_chars
    )
    
    prompt = f"Research:\n{p.report_text}\n"

    gen_cfg = GenerationConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
        response_mime_type="application/json",
    )

    resp = model.generate_content(contents=[system_prompt, prompt], generation_config=gen_cfg)
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
            # Optional: Trim script length if it exceeds the max
            for section in res.sections:
                if len(section.script) > p.max_script_chars:
                    section.script = section.script[: p.max_script_chars].rstrip()
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