from __future__ import annotations
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, constr, HttpUrl

# ---------- LLM summarize (Gemini 1.5) ---------------------------------------

class SummarizeParams(BaseModel):
    report_text: constr(min_length=50, max_length=60_000)
    max_bullets: int = Field(default=5, ge=3, le=8)
    max_script_chars: int = Field(default=700, ge=200, le=900)

class SummarizeResult(BaseModel):
    title: constr(min_length=3, max_length=100)
    subtitle: constr(min_length=3, max_length=140)
    bullets: List[constr(min_length=3, max_length=160)] = Field(min_length=3, max_length=8)
    script: constr(min_length=20, max_length=900)
    image_prompt: constr(min_length=10, max_length=600)

# ---------- Image.generate (Vertex Imagen) -----------------------------------

class GenerateImageParams(BaseModel):
    prompt: constr(min_length=10, max_length=600)
    aspect: Literal["16:9","1:1","4:3"] = "16:9"
    safety_tier: Literal["default","block_only_high","block_most"] = "default"
    return_drive_link: bool = False

class GenerateImageResult(BaseModel):
    local_path: Optional[constr(min_length=3, max_length=2048)] = None
    drive_file_id: Optional[str] = None
    url: Optional[HttpUrl] = None

# ---------- Slides.create (single-slide deck) --------------------------------

class SlidesCreateParams(BaseModel):
    client_request_id: Optional[constr(strip_whitespace=True, min_length=6, max_length=64)] = None
    title: constr(min_length=3, max_length=100)
    subtitle: constr(min_length=0, max_length=140) = ""
    bullets: List[constr(min_length=3, max_length=160)] = Field(min_length=1, max_length=8)
    script: Optional[constr(min_length=0, max_length=700)] = None

    image_local_path: Optional[constr(strip_whitespace=True, min_length=3, max_length=1024)] = None
    image_url: Optional[HttpUrl] = None
    image_drive_file_id: Optional[constr(strip_whitespace=True, min_length=10, max_length=200)] = None

    aspect: Literal["16:9","4:3"] = "16:9"
    share_image_public: bool = True

class SlidesCreateResult(BaseModel):
    presentation_id: str
    slide_id: str
    url: HttpUrl
    reused_existing: bool = False
