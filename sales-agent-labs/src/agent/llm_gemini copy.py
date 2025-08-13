from __future__ import annotations
import json
import logging
from typing import Any, Dict, List
from tenacity import retry, stop_after_attempt, wait_exponential
import google.generativeai as genai
from .config import settings

log = logging.getLogger("agent.llm_gemini")

def _configure() -> None:
    if not settings.GOOGLE_API_KEY:
        raise RuntimeError("Missing GOOGLE_API_KEY in .env")
    genai.configure(api_key=settings.GOOGLE_API_KEY)

def _model(response_mime_type: str= "application/json"):
    """Create a model with JSON-only output. We keep temperature low for consistency.
    """
    return genai.GenerativeModel(
        model_name=settings.LLM_MODEL,
        generation_config={
            "temperature":0.2,
            "response_mime_type": response_mime_type, # asks Gemini to produce JSON only
        }
    )
def _parse_json(text:str)-> Dict[str,Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        snippet = (text or "")[:200].replace("\n", " ")
        log.warning("JSON parse failed: %s (snippet=%r)", e, snippet)
        raise

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.6, min=0.6, max=3))
def generate_json(system_instruction: str, user_text:str) -> Dict[str, Any]:
    """
    Call Gemini and return parsed JSON, with retries for transient failure
    or malformed JSON (rare with response_mime_type).
    """
    _configure()
    model = _model(response_mime_type="application/json")
    # For gemini-1.5, you can pass a system instruction directly:
    response= model.generate_content(
        contents=[
            {"role": "user", "parts": [system_instruction]},
            {"role": "user", "parts": [user_text]}
        ]
    )
    # response.text is the aggregated text
    return _parse_json(response.text or "")

