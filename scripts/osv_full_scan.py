"""
Fetch all package names from the OSSF malicious-packages OSV repo and run
Slopspotter deep scans for each (PyPI and/or npm). Results are appended as
newline-delimited JSON for easy resume/review.

Usage examples:
  python scripts/osv_full_scan.py --ecosystem pypi --out osv_pypi.ndjson --limit 50
  python scripts/osv_full_scan.py --ecosystem npm  --out osv_npm.ndjson  --risk high --score 0.9
  python scripts/osv_full_scan.py --ecosystem all  --out osv_all.ndjson
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path
from typing import Iterable, List, Set, Tuple

# Ensure we can import slopspotter from the mono-repo layout
ROOT = Path(__file__).resolve().parents[1]
CLI_SRC = ROOT / "slopspotter-cli" / "src"
if str(CLI_SRC) not in sys.path:
    sys.path.insert(0, str(CLI_SRC))

from slopspotter import vm_sandbox  # type: ignore  # noqa: E402

OSV_API = "https://api.github.com/repos/ossf/malicious-packages/contents/osv/malicious/{eco}?ref=main"


def fetch_osv_packages(ecosystem: str) -> List[str]:
    url = OSV_API.format(eco=ecosystem)
    with urllib.request.urlopen(url) as resp:
        data = json.load(resp)
    return [item["name"] for item in data if item.get("type") == "dir"]


def load_seen(out_path: Path) -> Set[Tuple[str, str]]:
    seen: Set[Tuple[str, str]] = set()
    if not out_path.exists():
        return seen
    for line in out_path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            pkg = obj.get("package")
            lang = obj.get("language") or (obj.get("payload") or {}).get("language")
            if pkg and lang:
                seen.add((pkg, str(lang).lower()))
        except json.JSONDecodeError:
            continue
    return seen


def build_worklist(ecosystem: str) -> List[Tuple[str, str]]:
    work: List[Tuple[str, str]] = []
    if ecosystem in ("pypi", "all"):
        for name in fetch_osv_packages("pypi"):
            work.append((name, "python"))
    if ecosystem in ("npm", "all"):
        for name in fetch_osv_packages("npm"):
            work.append((name, "javascript"))
    return work


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan all OSSF malicious packages via Slopspotter")
    parser.add_argument("--ecosystem", choices=["pypi", "npm", "all"], default="all", help="Which ecosystem to scan")
    parser.add_argument("--risk", default="high", help="Risk level context passed to sandbox")
    parser.add_argument("--score", type=float, default=0.9, help="Prior score context passed to sandbox")
    parser.add_argument("--limit", type=int, help="Optional limit on number of packages to scan")
    parser.add_argument("--out", type=str, default="osv_scan_results.ndjson", help="Output NDJSON path (append/resume)")
    args = parser.parse_args()

    out_path = Path(args.out)
    seen = load_seen(out_path)

    work = build_worklist(args.ecosystem)
    if args.limit:
        work = work[: args.limit]

    # Filter out already-scanned package/language combos (for resume)
    todo = [(pkg, lang) for pkg, lang in work if (pkg, lang.lower()) not in seen]
    if not todo:
        print("Nothing to scan (all tasks already in output).")
        return 0

    print(f"Scanning {len(todo)} package(s); writing to {out_path}", flush=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as fh:
        for idx, (pkg, lang) in enumerate(todo, start=1):
            t0 = time.monotonic()
            payload = {"packageName": pkg, "language": lang, "context": {"riskLevel": args.risk, "score": args.score, "originalLanguage": lang}}
            try:
                result = vm_sandbox.handle_deep_scan_request(payload)
            except Exception as exc:  # keep going on errors
                result = {"success": False, "error": str(exc)}
            elapsed = time.monotonic() - t0
            record = {"package": pkg, "language": lang, "payload": payload, "response": result, "elapsed": elapsed}
            fh.write(json.dumps(record) + "\n")
            fh.flush()

            # Console summary (flush to keep logs informative)
            success = result.get("success", False) if isinstance(result, dict) else False
            verdict = result.get("result", {}).get("isMalicious") if isinstance(result, dict) else None
            conf = result.get("result", {}).get("confidence") if isinstance(result, dict) else None
            print(f"[{idx}/{len(todo)}] {pkg} ({lang}) -> success={success} verdict={verdict} conf={conf} elapsed={elapsed:.1f}s", flush=True)
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
