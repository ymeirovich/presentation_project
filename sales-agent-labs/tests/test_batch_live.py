import os, pytest, importlib


def _env_ready() -> bool:
    return bool(os.getenv("RUN_SMOKE") == "1" and os.getenv("GOOGLE_CLOUD_PROJECT"))


@pytest.mark.skipif(
    not _env_ready(), reason="Set RUN_SMOKE=1 and GOOGLE_CLOUD_PROJECT to run"
)
def test_batch_two_reports_live_smoke(tmp_path):
    txt1 = tmp_path / "a.txt"
    txt2 = tmp_path / "b.txt"
    txt1.write_text(
        "AlphaCo modernizes data stack to cut costs and increase governance.",
        encoding="utf-8",
    )
    txt2.write_text(
        "BetaBank upgrades analytics for faster reporting and better compliance.",
        encoding="utf-8",
    )

    orch = importlib.import_module("src.mcp_lab.orchestrator")
    items = [
        (txt1.name, txt1.read_text(encoding="utf-8")),
        (txt2.name, txt2.read_text(encoding="utf-8")),
    ]
    results = orch.orchestrate_many(items, sleep_between_secs=0.1)
    assert len(results) == 2
    assert any(r["ok"] and r.get("url") for r in results)
