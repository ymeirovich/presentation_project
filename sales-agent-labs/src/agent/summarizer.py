from __future__ import annotations
import logging
from typing import Dict, Any, List
from pydantic import ValidationError
from .prompts import SYSTEM_PROMPT, build_user_prompt
from .llm import chat_json
from .models import SalesSlide # Day 5 (Option B) model

log = logging.getLogger("agent.summarizer")
def _messages_for_report(report_text:str) -> List[Dict[str,str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role":"user", "content": build_user_prompt(report_text)}
    ]

def _messages_for_repair(report_text: str, bad_json: Dict[str, Any], errors: List[str]) -> List[Dict[str,str]]:
    # Tell the model exactly what failed and ask for corrected JSON only.
    repair_instruction = (
        "Your previous output failed validation. Fix the issues listed below and return ONLY the corrected JSON "
        "matching the required schema exactly. Do not include any explanation or extra keys. \n\n"
        "Validation errors:\n- " + "\n- ".join(errors) + "\n\n"
        "Here was your previous JSON (for reference):\n" + str(bad_json)
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(report_text)},
        {"role": "assistant", "content": str(bad_json)},   # show what it said
        {"role": "user", "content": repair_instruction},
    ]

def summarize_report_to_sales_slide(report_text: str, *, attempts: int=2) -> SalesSlide:
    """
    Generate a SalesSlide from freeform report text, enforce schema, 
    and attempt auto-repair once if validation fails.
    """
    # 1) Fierst attempt
    msgs = _messages_for_report(report_text)
    raw = chat_json(msgs)

    try:
        return SalesSlide(**raw)
    except ValidationError as e:
        if attempts <=1:
            raise

        # 2) Auto-repair attempt with explicit errors
        errors = []
        for err in e.errors():
            loc = ".".join(str(p) for p in err.get("loc",()))
            errors.append(f"{loc}: {err.get('msg')}")

        msgs2 = _messages_for_repair(report_text, raw, errors)
        raw2 = chat_json(msgs2)

        # Final validation (raise if sstill bad)
        return SalesSlide(**raw2)
    
    

