from __future__ import annotations

# The SalesSlide JSON the LLM must return
JSON_SCHEMA_HINT = """Return ONLY valid JSON with this exact shape:
{
    "title": "string (<=120 characters)",
    "subtitle": "string (<=160 characters)",
    "bullets": [
        "string",
        "string",
        "string"
    ],
    "script": "string (<=160 words, ~75 seconds)",
    "image_prompt": "string (<=200 characters)",
    "image_url": "string"
}
No extra keys. No markdown. No comments. JSON only.
"""

SYSTEM_PROMPT = f"""
- Focus on the core value proposition for the prospect.annotations
- Use clear, specific, jargon-light language.annotations
- 3-5 bullets max. No fluff.
- "script" must be <= 160 words (about 75 seconds).
- Return JSON only. Do not include any text before/after the JSON.

{JSON_SCHEMA_HINT}
""".strip()

def build_user_prompt(report_text: str) -> str:
    """
    Build the user message. We keep it simple and deterministic."""
    return f"""
Here is the Deep Research report. Summarize it into a single compelling slide.

Report:
{report_text}

Remember:
- 3-5 bullets
- <=160 words for "script"
- Return only the JSON object, nothing else.
""".strip()