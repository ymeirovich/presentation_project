import os, pytest, importlib

def _env_ready() -> bool:
    return bool(os.getenv("RUN_SMOKE") == "1" and os.getenv("GOOGLE_CLOUD_PROJECT"))

@pytest.mark.skipif(not _env_ready(), reason="Set RUN_SMOKE=1 and GOOGLE_CLOUD_PROJECT to run")
def test_orchestrator_live_smoke():
    orch = importlib.import_module("src.mcp_lab.orchestrator")
    demo_text = (
        "Acme FinTech is modernizing ETL to reduce infrastructure spend and speed insights. "
        "Priority: cost reduction, compliance risk, faster analytics. "
        "Current stack: fragmented pipelines; goal: consolidation and governance."
    )
    res = orch.orchestrate(demo_text)
    assert "presentation_id" in res and "slide_id" in res and "url" in res
