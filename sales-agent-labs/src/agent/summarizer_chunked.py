from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Tuple

from .chunking import chunk_text
from .prompts import (
    SYSTEM_FOR_CHUNKS,
    SYSTEM_FOR_SYNTHESIS,
    build_user_for_chunk,
    build_user_for_synthesis,
)
from .llm_gemini import generate_json
from .models import SalesSlide  # Day5 (pydantic model)
from pydantic import ValidationError

log = logging.getLogger("agent.summerizer_chunked")


async def _summarize_one_chunk(chunk_text: str) -> Dict[str, Any]:
    """
    Call Gemini synchronously via a thread to avoid blocking the event loop.
    We keep this wrapper thin; generate_json already retries and returns dict.
    """

    def call() -> Dict[str, Any]:
        return generate_json(
            system_instruction=SYSTEM_FOR_CHUNKS,
            user_text=build_user_for_chunk(chunk_text),
        )

    return await asyncio.to_thread(call)


async def summarize_chunks_concurrently(
    chunks: List[str], max_concurrency: int = 5
) -> List[Dict[str, Any]]:
    sem = asyncio.Semaphore(max_concurrency)

    async def guarded(c: str) -> Dict[str, Any]:
        async with sem:
            return await _summarize_one_chunk(c)

    tasks = [asyncio.create_task(guarded(c)) for c in chunks]
    results: List[Dict[str, Any]] = []
    errors: List[Exception] = []

    for t in asyncio.as_completed(tasks):
        try:
            results.append(await t)
        except Exception as e:
            errors.append(e)

    if errors:
        # Surface the first; you could aggregate/log all
        raise errors[0]
    return results


# --- Synthesis and validation----
def _synthesize_slide(per_chunk_json: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    One-shot synthesis call to produce the SalesSlide JSON (dict).
    """
    return generate_json(
        system_instruction=SYSTEM_FOR_SYNTHESIS,
        user_text=build_user_for_synthesis(per_chunk_json),
    )


def _validate_sales_slide(payload: Dict[str, Any]) -> SalesSlide:
    """
    Enforce schema and word caps using your Day-5 pydantic model.
    """
    return SalesSlide(**payload)


async def summarize_report_chunked(report_text: str) -> SalesSlide:
    """
    1) Chunk -> 2) per-chunk summaries (concurrent) -> 3) synthesis -> 4) validation
    """
    # 1) chunk
    chunks = chunk_text(report_text, max_words=350)
    log.info("Chunked report into %d chunks", len(chunks))

    # 2) Concurrent per-chunk summarization
    per_chunk = await summarize_chunks_concurrently(chunks, max_concurrency=5)

    # 3) Synthesis
    draft = _synthesize_slide(per_chunk)

    # 4) Validation (raise if invalid)
    try:
        return _validate_sales_slide(draft)
    except ValidationError as e:
        # Optionally: feed errors back to Gemini for a repair attempt (Day 6 pattern)
        # For now, surface the error to the caller so you can see exactly what failed.
        msgs = [f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()]
        raise RuntimeError("Synthesis failed validation:\n-" + "\n-".join(msgs)) from e
