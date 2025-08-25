from __future__ import annotations
from typing import Any, Dict, List

# Custom error so callers can catch validation issues explicitly


class ValidationError(Exception):
    """Raised when the payload volates the schema contract."""

    def __init__(self, errors: List[str]):
        super().__init__("\n".join(errors))
        self.errors = errors


# --- small pure helpers ---


def _word_count(s: str) -> int:
    # split() handles multiple spaces / newlines
    return len(s.split())


def _trim_to_words(s: str, max_words: int) -> str:
    words = s.split()
    if len(words) <= max_words:
        return s.strip()
    return " ".join(words[:max_words]).strip()


def _is_nonempty_string(x: Any) -> bool:
    return isinstance(x, str) and x.strip() != ""


def _normalize_list_of_strings(items: List[str]) -> List[str]:
    """keep only strings, strip whitespace, drop empties"""
    normed = [i.strip() for i in items if isinstance(i, str)]
    return [i for i in normed if i]


# contract & validator

_ALLOWED_KEYS = {"title", "subtitle", "bullets", "script", "image_prompt"}


def validate_sales_slide_payload(
    payload: Dict[str, Any], *, trim_script: bool = True, forbid_extra: bool = True
) -> Dict[str, Any]:
    """
    Validate & normalize a one-slide sales payload.
    Requires:
    - title: non-empty str, len<=120
    - subtitle: non-empty str, len<=160
    - bullets: list[str] with 3..5 non-empty items
    - script: str with<= 160 words (trim or error)
    - image_prompt: non-empty str
    - extra fields: forbidden (default)
    """

    errors: List[str] = []
    clean: Dict[str, Any] = {}

    # 1) extra fields
    extra = set(payload.keys()) - _ALLOWED_KEYS
    if extra and forbid_extra:
        errors.append(f"Unknown fields: {sorted(extra)}")

    # 2) title
    title = payload.get("title")
    if not _is_nonempty_string(title):
        errors.append("'title' must be a non-empty string")
    else:
        title = title.strip()
        if len(title) > 120:
            errors.append("'title' must be <= 120 characters")
        else:
            clean["title"] = title

    # 3) subtitle
    subtitle = payload.get("subtitle")
    if not _is_nonempty_string(subtitle):
        errors.append("'subtitle' must be a non-empty string")
    else:
        subtitle = subtitle.strip()
        if len(subtitle) > 160:
            errors.append("'subtitle' must be <= 160 characters")
        else:
            clean["subtitle"] = subtitle

    # 4) bullets
    bullets = payload.get("bullets", [])
    if not isinstance(bullets, list):
        errors.append("'bullets' must be a list of strings")
    else:
        bullets = _normalize_list_of_strings(bullets)
        if not (3 <= len(bullets) <= 5):
            errors.append("'bullets' must have 3 to 5 non-empty items")
        else:
            clean["bullets"] = bullets

    # 5) script
    script = payload.get("script")
    if not isinstance(script, str):
        errors.append("'script' must be a string <= 160 words")
    else:
        script = script.strip()
        wc = _word_count(script)
        if wc > 160:
            if trim_script:
                script = _trim_to_words(script, 160)
            else:
                errors.append(f"'script' is {wc} words; must be <= 160")
            if script == "":
                errors.append("'script' must not be empty after trimming")
            else:
                clean["script"] = script

    # 6) image_prompt
    image_prompt = payload.get("image_prompt")
    if not _is_nonempty_string(image_prompt):
        errors.append("'image_prompt' must be a non-empty string")
    else:
        clean["image_prompt"] = image_prompt
    if errors:
        # One exception with all issues --> better user experience
        raise ValidationError(errors)
    return clean
