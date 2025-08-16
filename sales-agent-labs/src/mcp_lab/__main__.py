from __future__ import annotations
import argparse, pathlib, sys, logging
from typing import List, Tuple

from .orchestrator import orchestrate, orchestrate_many

log = logging.getLogger("orchestrator.cli")

def _collect_reports(targets: List[str]) -> List[Tuple[str, str]]:
    """Accept files and/or a directory; returns [(name, text), ...]"""
    items: List[Tuple[str, str]] = []
    for t in targets:
        p = pathlib.Path(t)
        if p.is_dir():
            for f in sorted(p.glob("*.txt")):
                items.append((f.name, f.read_text(encoding="utf-8")))
        elif p.is_file():
            items.append((p.name, p.read_text(encoding="utf-8")))
        else:
            print(f"Warning: not found or unsupported path: {p}", file=sys.stderr)
    if not items:
        print("No input reports found.", file=sys.stderr)
        sys.exit(2)
    return items

def main():
    ap = argparse.ArgumentParser(description="Run the Report → Slide Deck orchestrator")
    ap.add_argument("inputs", nargs="+", help="One or more report files or a directory of .txt files")
    ap.add_argument("--request-id", help="Optional idempotency key (single-file mode only)")
    ap.add_argument("--sleep-between", type=float, default=0.0, help="Seconds to sleep between reports (quota-friendly)")
    args = ap.parse_args()

    items = _collect_reports(args.inputs)

    # Single-file path preserves --request-id behavior
    if len(items) == 1 and args.request_id:
        name, text = items[0]
        res = orchestrate(text, client_request_id=args.request_id)
        print("✅ Deck ready:", res.get("url") or "(no URL?)")
        return

    # Batch path
    results = orchestrate_many(items, sleep_between_secs=args.sleep_between)
    print("\nBatch summary:")
    for r in results:
        status = "OK" if r["ok"] else "FAIL"
        print(f"- {status} {r['name']}: {r.get('url') or r.get('error')}")
    ok = sum(1 for r in results if r["ok"])
    print(f"\n✅ {ok}/{len(results)} reports succeeded.")

if __name__ == "__main__":
    main()
