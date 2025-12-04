"""
Run a deep scan from the CLI and print the raw result.

Usage:
  python scripts/deep_scan_debug.py --package requests --language python --risk low --score 0.0
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Ensure we can import slopspotter from the mono-repo layout
ROOT = Path(__file__).resolve().parents[1]
CLI_SRC = ROOT / "slopspotter-cli" / "src"
if str(CLI_SRC) not in sys.path:
    sys.path.insert(0, str(CLI_SRC))

from slopspotter import vm_sandbox  # type: ignore  # noqa: E402


def touch_logfile(log_path: Path) -> None:
    """Create the log file if it doesn't exist, so tailing works."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if not log_path.exists():
        log_path.write_text("")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deep scan and print result")
    parser.add_argument("--package", required=True, help="Package name to scan")
    parser.add_argument(
        "--language",
        default="python",
        choices=["python", "py", "javascript", "js", "node", "npm", "typescript", "ts"],
        help="Package language",
    )
    parser.add_argument("--risk", default="low", help="Heuristic riskLevel (low/medium/high)")
    parser.add_argument("--score", type=float, default=0.0, help="Heuristic score (0-1)")
    parser.add_argument(
        "--log-file",
        default=str(Path.home() / "Desktop" / "slopspotter_debug.log"),
        help="Path to the debug log file (to tail in another shell)",
    )
    args = parser.parse_args()

    log_path = Path(args.log_file)
    touch_logfile(log_path)

    ctx = {"riskLevel": args.risk, "score": args.score}
    result = vm_sandbox.handle_deep_scan_request(
        {"packageName": args.package, "language": args.language, "context": ctx}
    )
    print(json.dumps(result, indent=2))
    print(f"\nLog file: {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
