from __future__ import annotations
import argparse, pathlib, sys, logging
from .orchestrator import orchestrate

log = logging.getLogger("orchestrator.cli")

def main():
    ap = argparse.ArgumentParser(description="Run the Report → Slide Deck orchestrator")
    ap.add_argument("report_path", help="Path to a text file with the prospect research")
    ap.add_argument("--request-id", help="Optional idempotency key (defaults to a UUID)")
    args = ap.parse_args()

    path = pathlib.Path(args.report_path)
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(2)

    report_text = path.read_text(encoding="utf-8")
    res = orchestrate(report_text, client_request_id=args.request_id)
    url = res.get("url")
    print("✅ Deck ready:", url or "(no URL?)")

if __name__ == "__main__":
    main()
