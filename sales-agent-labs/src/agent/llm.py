from __future__ import annotations
import json
import logging
from typing import List, Any, Dict
import google.generativeai as genai
from .config import settings

log = logging.getLogger("agent.llm")

def _client() -> None:
    if not settings.GOOGLE_API_KEY:
        raise RuntimeError("Missing GOOGLE_API_KEY in environment")
    genai.configure(api_key=settings.GOOGLE_API_KEY)

def _parse_json(s:str) -> Dict[str, Any]:
    try:
        # Gemini may return the json in a code block, so we need to strip it
        s = s.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(s)
    except json.JSONDecodeError as e:
        # Log a short snippet for debugging (avoid logging entire output)
        snippet = s[:200].replace("\n", " ")
        log.warning("JSON parse failed: %s (snippet: %r)", e, snippet)
        raise

def chat_json(messages: List[Dict[str, str]], *, response_format_json: bool=True) -> Dict[str, Any]:
    """
    Call the model and return parsed JSON.
    messages: list like [{"role":"user", "parts": ["..."]}]
    """
    _client()
    model = genai.GenerativeModel(settings.LLM_MODEL)

    # The Gemini API has a different message format than OpenAI
    # We need to convert the messages to the correct format.
    # We are assuming the last message is the user prompt and the rest is history.
    
    history = []
    for message in messages[:-1]:
        if message['role'] == 'user':
            history.append({'role': 'user', 'parts': [message['content']]})
        elif message['role'] == 'assistant':
            history.append({'role': 'model', 'parts': [message['content']]})

    prompt = messages[-1]['content']

    chat = model.start_chat(history=history)
    
    resp = chat.send_message(prompt)
    text = resp.text or ""
    return _parse_json(text)
