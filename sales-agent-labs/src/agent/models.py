from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List


class SalesSlide(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)  # auto-trim strings

    title: str = Field(min_length=1, max_length=120)
    subtitle: str = Field(min_length=1, max_length=160)
    bullets: List[str] = Field(min_length=3, max_length=5)
    script: str  # <= 160 words
    image_prompt: str = Field(min_length=1)

    @field_validator("script")
    @classmethod
    def script_word_limit(cls, v: str) -> str:
        words = v.split()
        if len(words) > 160:
            # choose: raise OR trim; here we trim to keep flow moving
            v = " ".join(words[:160])
        return v
