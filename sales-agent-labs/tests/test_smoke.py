# tests/test_smoke.py
from __future__ import annotations
import os
import json
import importlib
import pathlib
import pytest


def _env_reason() -> str | None:
    """
    Return None if env looks ready for a live smoke test, else a reason string.
    We require:
      - GOOGLE_CLOUD_PROJECT set
      - Either GOOGLE_APPLICATION_CREDENTIALS points to an existing file
        OR we're running on a GCP environment with ADC (not checked here).
    """
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project:
        return "GOOGLE_CLOUD_PROJECT is not set"

    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path:
        if not pathlib.Path(creds_path).expanduser().exists():
            return f"GOOGLE_APPLICATION_CREDENTIALS points to a missing file: {creds_path}"
        # looks good
        return None

    # No explicit creds path; allow if running with ADC on GCP (Cloud Run/GCE/GKE).
    # We can't reliably detect metadata server without network access in tests,
    # so we require explicit creds for local runs.
    return "GOOGLE_APPLICATION_CREDENTIALS not set (ADC via gcloud/metadata not detected in tests)"


def test_registry_contains_tools():
    """Quick sanity check: server exposes required MCP tools."""
    server = importlib.import_module("src.mcp.server")
    assert hasattr(server, "TOOLS"), "MCP server should define a TOOLS registry"
    for name in ("llm.summarize", "image.generate", "slides.create"):
        assert name in server.TOOLS, f"Missing tool in registry: {name}"


def test_schema_roundtrip_minimal():
    """Local-only: ensure Pydantic models import and basic validation works."""
    schemas = importlib.import_module("src.mcp.schemas")

    # Construct a minimal valid result (no network calls)
    result = schemas.SummarizeResult(
        title="Acme FinTech: Streamline ETL",
        subtitle="Reduce cost, risk, and time-to-insight",
        bullets=["Lower infra spend", "Faster analytics", "Better governance"],
        script="Short presenter notes for a ~75-second talk.",
        image_prompt="A clean, professional dashboard illustration"
    )
    dumped = result.model_dump()
    assert isinstance(dumped, dict)
    assert "title" in dumped and "bullets" in dumped


@pytest.mark.skipif(os.getenv("RUN_SMOKE") != "1", reason="Set RUN_SMOKE=1 to run live integration smoke test")
def test_live_end_to_end_orchestrator():
    """
    Live smoke test (opt-in):
      - Calls MCP server via the orchestrator client
      - Gemini 1.5 → Imagen → Slides (single slide)
      - Asserts presentation_id/slide_id/url in response
    """
    reason = _env_reason()
    if reason:
        pytest.skip(f"Skipping live smoke: {reason}")

    orch = importlib.import_module("src.mcp_lab.client_orchestrator")

    demo_text = (
        "Acme FinTech is modernizing ETL to reduce infrastructure spend and speed insights.\n"
        "Priority: cost reduction, compliance risk, faster analytics.\n"
        "Current stack: fragmented pipelines; goal: consolidation and governance."
    )

    result = orch.orchestrate(demo_text)

    # Basic shape assertions (don’t overfit to transient IDs)
    assert isinstance(result, dict), f"Expected dict result, got: {type(result)}"
    for key in ("presentation_id", "slide_id", "url"):
        assert key in result and result[key], f"Missing {key} in orchestrator result: {json.dumps(result, indent=2)}"

    # Optional sanity on URL shape
    assert str(result["url"]).startswith("https://docs.google.com/presentation/") or \
           "docs.google.com" in str(result["url"]), f"Unexpected Slides URL: {result['url']}"
