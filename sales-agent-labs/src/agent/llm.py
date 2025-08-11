from __future__ import annotations
import json
import logging
from typing import List, Any, Dict
from tenacity import retry, stop_after_attempt, wait_exponential
from openai import OpenAI
from .config import settings

log = logging.getLogger("agent.llm")
def _client() -> OpenAI:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("Missing OPENAI_API_KEY in environment")
    return OpenAI(api_key=settings.OPENAI_API_KEY)

def _parse_json(s:str) -> Dict[str, Any]:
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        # Log a short snippet for debugging (avoid logging entire output)
        snippet = s[:200].replace("\n", " ")
        log.warning("JSON parse failed: %s (snippet: %r)", e, snippet)
        raise 

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.6, min=0.6, max=3))
def chat_json(messages: List[Dict[str, str]], *, response_format_json: bool=True) -> Dict[str, Any]:
    """
    Call the model and return parsed JSON. Retries on transient failures or bad JSON.
    messages: list like [{"role":"system", "content":"..."], {"role":"user", "content":"..."}]}]
    """
    client = _client()

    #Prefer JSON mode when available on your model
    kwargs = {
        "model": settings.LLM_MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 700, #enough for our JSON
    }
    if response_format_json:
        #Chat completions JSON mode
        kwargs["response_format"] = {"type":"json_object"}

    resp= client.chat.completions.create(**kwargs)
    text = resp.choices[0].message.content or ""
    return _parse_json(text)


