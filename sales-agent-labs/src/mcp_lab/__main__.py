from __future__ import annotations
import argparse, pathlib, sys, logging
from .orchestrator import orchestrate

log = logging.getLogger("orchestrator.cli")

def main():
    ap = argparse.ArgumentParser(description="Run the Report → Slide Deck orchestrator")
    ap.add_argument("report_path", help="Path to a text file with the prospect research")
    ap.add_argument("--request-id", help="Optional idempotency key (defaults to a UUID)")
    ap.add_argument("--no-cache", action="store_true", help="Disable local result caching")
    ap.add_argument("--cache-ttl-hours", type=float, default=1.0, help="Cache TTL in hours (default: 1h)")
    args = ap.parse_args()

    path = pathlib.Path(args.report_path)
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(2)

    report_text = path.read_text(encoding="utf-8")
    res = orchestrate(
        report_text,
        client_request_id=args.request_id,
        use_cache=not args.no_cache,                  # ← correct kwarg name
        cache_ttl_secs=args.cache_ttl_hours * 3600.0  # ← correct kwarg name/units
    )
    print("✅ Deck ready:", res.get("url") or "(no URL?)")

if __name__ == "__main__":
    main()
