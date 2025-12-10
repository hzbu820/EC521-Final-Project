"""
Batch deep scan helper to exercise multiple packages (e.g., known malicious samples)
through Slopspotter's Docker sandbox.

Examples:
  python scripts/malicious_batch_scan.py
  python scripts/malicious_batch_scan.py --packages automsg adafruit-imageload
  python scripts/malicious_batch_scan.py --file ./packages.txt --language javascript --out results.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

# Ensure we can import slopspotter from the mono-repo layout
ROOT = Path(__file__).resolve().parents[1]
CLI_SRC = ROOT / "slopspotter-cli" / "src"
if str(CLI_SRC) not in sys.path:
    sys.path.insert(0, str(CLI_SRC))

from slopspotter import vm_sandbox  # type: ignore  # noqa: E402

DEFAULT_PACKAGES = [
    # PyPI malicious samples from ossf/malicious-packages
    "automsg",
    "adafruit-imageload",
    "anrok",
    "anothertestproject",
    "beaautifulsoup",
    "bytepilot",
]


def normalize_language(lang: str) -> str:
    lang_lower = lang.lower()
    if lang_lower in ("python", "py"):
        return "python"
    if lang_lower in ("javascript", "js", "node", "npm", "typescript", "ts"):
        return "javascript"
    raise argparse.ArgumentTypeError(f"Unsupported language: {lang}")


def load_packages(args: argparse.Namespace) -> list[str]:
    pkgs: set[str] = set()
    if args.packages:
        pkgs.update(args.packages)
    if args.file:
        for line in Path(args.file).read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            pkgs.add(stripped)
    if not pkgs:
        pkgs.update(DEFAULT_PACKAGES)
    return sorted(pkgs)


def iter_scans(packages: Iterable[str], language: str, risk: str, score: float):
    context = {"riskLevel": risk, "score": score, "originalLanguage": language}
    for pkg in packages:
        payload = {"packageName": pkg, "language": language, "context": context}
        result = vm_sandbox.handle_deep_scan_request(payload)
        yield pkg, payload, result


def format_summary(pkg: str, result: dict) -> str:
    if not result.get("success"):
        return f"[{pkg}] ERROR: {result.get('error', 'unknown error')}"

    body = result.get("result", {})
    malicious = body.get("isMalicious")
    confidence = body.get("confidence")
    indicators = body.get("indicators") or []
    endpoints = body.get("networkConnections") or []
    tag = "MALICIOUS" if malicious else "benign?"
    conf_txt = f"{confidence:.2f}" if isinstance(confidence, (int, float)) else "n/a"
    ind_txt = "; ".join(indicators[:3])
    return f"[{pkg}] {tag} conf={conf_txt} net={len(endpoints)} indicators={ind_txt}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run batch deep scans via Slopspotter")
    parser.add_argument("--packages", nargs="+", help="Package names to scan (space-separated)")
    parser.add_argument("--file", type=str, help="Optional file with one package name per line")
    parser.add_argument("--language", default="python", help="Language (python/javascript/typescript)")
    parser.add_argument("--risk", default="high", help="Risk level to feed into context (low/medium/high)")
    parser.add_argument("--score", type=float, default=0.9, help="Prior score to feed into context (0-1)")
    parser.add_argument(
        "--out",
        type=str,
        default=str(Path("batch_scan_results.json")),
        help="Where to write the full JSON results",
    )
    args = parser.parse_args()

    language = normalize_language(args.language)
    packages = load_packages(args)
    if not packages:
        print("No packages to scan. Provide --packages or --file.")
        return 1

    print(f"Scanning {len(packages)} packages as {language}...")
    records = []
    for pkg, payload, result in iter_scans(packages, language, args.risk, args.score):
        print(format_summary(pkg, result))
        records.append({"package": pkg, "payload": payload, "response": result})

    out_path = Path(args.out)
    out_path.write_text(json.dumps(records, indent=2))
    print(f"\nFull results written to: {out_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
