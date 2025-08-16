from __future__ import annotations
import json, logging, time, os
from typing import Any, Dict
from pydantic import ValidationError

from vertexai import init as vertex_init
from vertexai.generative_models import GenerativeModel
from ..schemas import SummarizeParams, SummarizeResult

log = logging.getLogger("mcp.tools.llm")

SYSTEM_INSTRUCTIONS = (
    "You are a sales enablement assistant. Read the prospect research and produce "
    "a crisp one-slide summary with: title, subtitle, 3-8 bullets (concise), a "
    "75-second presenter script (<= {max_script_chars} chars), and an image_prompt "
    "suitable for a modern, professional illustration. Return JSON only."
)

def _call_gemini_once(p: SummarizeParams) -> Dict[str, Any]:
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    region = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
    vertex_init(project=project, location=region)

    model = GenerativeModel("models/gemini-1.5-flash-latest")
    response = model.generate_content(
        contents=[{
            "role": "user",
            "parts": [
                {"text": SYSTEM_INSTRUCTIONS.format(max_script_chars=p.max_script_chars)},
                {"text": "\n\n--- RESEARCH TEXT ---\n"},
                {"text": p.report_text},
            ],
        }],
        generation_config={
            "temperature": 0.6,
            "max_output_tokens": 1024,
            "response_mime_type": "application/json",
            "response_schema": {
                "type": "object",
                "properties": {
                    "title": {"type":"string"},
                    "subtitle": {"type":"string"},
                    "bullets": {"type":"array","items":{"type":"string"}},
                    "script": {"type":"string"},
                    "image_prompt": {"type":"string"}
                },
                "required": ["title","subtitle","bullets","script","image_prompt"]
            },
        },
        safety_settings=None,
    )
    text = (response.text or "").strip()
    return json.loads(text)

def _retry_json_validate(p: SummarizeParams, attempts=3, base=0.6) -> SummarizeResult:
    last_err = None
    for i in range(attempts):
        try:
            raw = _call_gemini_once(p)
            return SummarizeResult.model_validate(raw)
        except (json.JSONDecodeError, ValidationError) as e:
            last_err = e
            delay = base * (2 ** i)
            log.warning("Gemini invalid JSON/schema (attempt %d/%d). Retry in %.2fs", i+1, attempts, delay)
            time.sleep(delay)
    raise RuntimeError(f"LLM structured output failed: {type(last_err).__name__}: {last_err}")

def llm_summarize_tool(params: dict) -> dict:
    p = SummarizeParams.model_validate(params)
    res = _retry_json_validate(p)
    return res.model_dump()
