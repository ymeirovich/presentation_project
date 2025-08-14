from __future__ import annotations
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, constr

# ---- JSON-RPC base types ----------------------------------------------------

class JsonRpcRequest(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: int
    method: constr(strip_whitespace=True, min_length=1)
    params: Optional[dict] = None

class JsonRpcErrorObj(BaseModel):
    code: int
    message: str
    data: Optional[dict] = None

class JsonRpcResponse(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: int
    result: Optional[dict] = None
    error: Optional[JsonRpcErrorObj] = None

# ---- Tool I/O schemas -------------------------------------------------------

class ReverseStringParams(BaseModel):
    text: constr(min_length=1, max_length=10_000)

class ReverseStringResult(BaseModel):
    reversed: str

class DraftSlideOutlineParams(BaseModel):
    # You’ll later feed the real “Deep Research report” text here.
    report_text: constr(min_length=1, max_length=50_000)
    max_bullets: int = Field(default=5, ge=3, le=10)

class DraftSlideOutlineResult(BaseModel):
    title: str
    subtitle: str
    bullets: List[str]
    # Not generating notes here; this just sketches the shape for later steps.
