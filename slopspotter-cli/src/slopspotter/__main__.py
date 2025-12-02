#!/usr/bin/env -S python3 -u
"""Main entry point for `slopspotter`."""

import argparse
import json
import logging
import os
import struct
import sys
import urllib.error
import urllib.request
from datetime import datetime
from importlib.metadata import metadata

from slopspotter import manifests
from slopspotter.constants import SLOPSPOTTER_VERSION, SUPPORTED_BROWSERS

logger = logging.getLogger(__name__)

logging.basicConfig(
    filename=os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "log.log"
    ),
    level=logging.DEBUG,
    encoding="utf-8",
    format="%(asctime)s - PID %(process)d [%(levelname)s]: %(message)s",
)


def get_message():
    """Read a message from stdin and decode it."""
    raw_length = sys.stdin.buffer.read(4)
    if len(raw_length) == 0:
        return ""
    message_length = struct.unpack("@I", raw_length)[0]
    message = sys.stdin.buffer.read(message_length).decode("utf-8")
    return json.loads(message)


def encode_message(message_content):
    """Encode a message for transmission, given its content.

    https://docs.python.org/3/library/json.html#basic-usage

    To get the most compact JSON representation, you should specify (',', ':')
    to eliminate whitespace. We want the most compact representation because
    the browser rejects # messages that exceed 1 MB.
    """
    logging.debug("encoding message")
    encoded_content = json.dumps(message_content, separators=(",", ":")).encode("utf-8")
    encoded_length = struct.pack("@I", len(encoded_content))
    return {"length": encoded_length, "content": encoded_content}


def send_message(encoded_message):
    """Send an encoded message to stdout."""
    sys.stdout.buffer.write(encoded_message["length"])
    sys.stdout.buffer.write(encoded_message["content"])
    sys.stdout.buffer.flush()


def loop() -> int:
    """Main background function."""
    while True:
        received_message = get_message()
        if received_message == "ping":
            logging.debug("received ping, sending pong")
            send_message(encode_message("pong"))
            continue

        # Command envelope from extension
        if isinstance(received_message, dict) and "type" in received_message:
            cmd_type = received_message.get("type")
            if cmd_type == "check-packages":
                logging.debug("received check-packages command")
                try:
                    response = handle_check_packages(received_message.get("payload", {}))
                    send_message(encode_message(response))
                except Exception as exc:  # noqa: BLE001
                    logging.exception("failed to handle check-packages: %s", exc)
                    send_message(encode_message({"error": "backend-scoring-error"}))
                continue

        # Unknown message; ignore to allow fallback on the frontend.
        continue
    return 0


def handle_check_packages(payload: dict) -> dict:
    """Build a structured response for check-packages command.

    Scoring mirrors the frontend heuristic so native responses can replace JS fallback.
    """
    snippet_id = payload.get("snippetId", "")
    packages = payload.get("packages", []) or []

    formatted = []
    for pkg in packages:
        name = pkg.get("name", "")
        language = pkg.get("language", "")
        result = build_heuristic_risk(name, language)
        formatted.append({"name": name, "language": language, "result": result})

    return {
        "snippetId": snippet_id,
        "packages": formatted,
        "warning": None,
    }


# ====== Heuristic scoring (mirrors frontend fallback) ======
NAME_TOKENS = ["installer", "updater", "crypto", "mining", "hack", "typo"]

STD_LIBS = {
    "python": {
        "abc",
        "argparse",
        "array",
        "asyncio",
        "base64",
        "collections",
        "concurrent",
        "contextlib",
        "copy",
        "csv",
        "datetime",
        "enum",
        "functools",
        "getopt",
        "getpass",
        "glob",
        "gzip",
        "hashlib",
        "heapq",
        "html",
        "http",
        "importlib",
        "io",
        "ipaddress",
        "itertools",
        "json",
        "logging",
        "math",
        "multiprocessing",
        "os",
        "pathlib",
        "pickle",
        "platform",
        "plistlib",
        "pprint",
        "queue",
        "random",
        "re",
        "selectors",
        "shlex",
        "signal",
        "socket",
        "sqlite3",
        "ssl",
        "statistics",
        "string",
        "struct",
        "subprocess",
        "sys",
        "tempfile",
        "textwrap",
        "threading",
        "time",
        "tkinter",
        "traceback",
        "typing",
        "unittest",
        "urllib",
        "uuid",
        "venv",
        "warnings",
        "weakref",
        "xml",
        "zipfile",
    }
}


def score_to_level(score: float) -> str:
    if score >= 0.7:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


def clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    return max(min_value, min(value, max_value))


def days_since(dt: datetime | None) -> float | None:
    if dt is None:
        return None
    return (datetime.utcnow() - dt).total_seconds() / 86400


def compute_name_risk(name: str) -> float:
    normalized = name.lower()
    risk = 0.0
    if any(token in normalized for token in NAME_TOKENS):
        risk += 0.5
    if len(normalized) > 18:
        risk += 0.2
    if any(char.isdigit() for char in normalized):
        risk += 0.15
    if "-" in normalized:
        risk += 0.1
    return clamp(risk)


def fetch_json(url: str, timeout: int = 3) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            if resp.status != 200:
                return None
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def extract_pypi_signals(name: str) -> dict:
    data = fetch_json(f"https://pypi.org/pypi/{name}/json")
    if not data:
        return {"exists": False}
    releases = data.get("releases", {}) or {}
    dates = []
    for files in releases.values():
        for file in files or []:
            upload_time = file.get("upload_time")
            if upload_time:
                try:
                    dates.append(datetime.fromisoformat(upload_time.replace("Z", "+00:00")))
                except ValueError:
                    continue
    dates.sort()
    first_release = dates[0] if dates else None
    last_release = dates[-1] if dates else None
    latest_files = releases.get(sorted(releases.keys())[-1], []) if releases else []
    has_sdist = any(f.get("packagetype") == "sdist" for f in latest_files or [])
    has_only_wheels = bool(latest_files) and all(
        f.get("packagetype") == "bdist_wheel" for f in latest_files or []
    )
    project_urls = data.get("info", {}).get("project_urls", {}) or {}
    has_any_project_url = any(isinstance(v, str) and v.strip() for v in project_urls.values())

    return {
        "exists": True,
        "firstRelease": first_release,
        "lastRelease": last_release,
        "releaseCount": len(releases),
        "hasOnlyWheels": has_only_wheels and not has_sdist,
        "hasRepo": bool(data.get("info", {}).get("home_page"))
        or bool(project_urls.get("Source"))
        or bool(project_urls.get("Homepage"))
        or has_any_project_url,
        "hasLicense": bool(
            isinstance(data.get("info", {}).get("license"), str)
            and len((data.get("info", {}) or {}).get("license", "").strip()) > 3
            and "unknown" not in (data.get("info", {}) or {}).get("license", "").lower()
        ),
    }


def extract_npm_signals(name: str) -> dict:
    registry = fetch_json(f"https://registry.npmjs.org/{name}")
    downloads = fetch_json(f"https://api.npmjs.org/downloads/point/last-week/{name}")
    if not registry:
        return {"exists": False}

    time = registry.get("time", {}) or {}
    version_dates = [
        datetime.fromisoformat(v.replace("Z", "+00:00"))
        for k, v in time.items()
        if k not in ("created", "modified")
    ]
    version_dates.sort()
    first_release = version_dates[0] if version_dates else None
    last_release = version_dates[-1] if version_dates else None
    latest_version = (registry.get("dist-tags") or {}).get("latest")
    latest_meta = (registry.get("versions") or {}).get(latest_version, {}) if latest_version else {}
    scripts = latest_meta.get("scripts") or {}
    has_install_scripts = "install" in scripts or "postinstall" in scripts
    weekly_downloads = downloads.get("downloads") if isinstance(downloads, dict) else None

    return {
        "exists": True,
        "firstRelease": first_release,
        "lastRelease": last_release,
        "releaseCount": len(version_dates),
        "hasInstallScripts": has_install_scripts,
        "hasRepo": bool(latest_meta.get("repository") or latest_meta.get("homepage")),
        "hasLicense": bool(latest_meta.get("license")),
        "weeklyDownloads": weekly_downloads,
    }


def extract_crates_signals(name: str) -> dict:
    data = fetch_json(f"https://crates.io/api/v1/crates/{name}")
    if not data:
        return {"exists": False}
    crate = data.get("crate") or {}
    first_release = None
    last_release = None
    if crate.get("created_at"):
        try:
            first_release = datetime.fromisoformat(crate["created_at"].replace("Z", "+00:00"))
        except ValueError:
            pass
    if crate.get("updated_at"):
        try:
            last_release = datetime.fromisoformat(crate["updated_at"].replace("Z", "+00:00"))
        except ValueError:
            pass
    return {
        "exists": True,
        "firstRelease": first_release,
        "lastRelease": last_release,
        "downloadCount": crate.get("downloads"),
        "hasRepo": bool(crate.get("repository") or crate.get("homepage")),
        "hasLicense": bool(crate.get("license")),
    }


def extract_go_signals(name: str) -> dict:
    try:
        with urllib.request.urlopen(f"https://proxy.golang.org/{name}/@v/list", timeout=3) as resp:
            if resp.status != 200:
                return {"exists": False}
            versions = [line.strip() for line in resp.read().decode("utf-8").splitlines() if line.strip()]
            return {
                "exists": True,
                "releaseCount": len(versions),
                "hasRepo": "." in name,
            }
    except urllib.error.URLError:
        return {"exists": False}


def registry_url_for(name: str, language: str) -> str | None:
    if language == "python":
        return f"https://pypi.org/project/{name}/"
    if language == "javascript":
        return f"https://www.npmjs.com/package/{name}"
    if language == "rust":
        return f"https://crates.io/crates/{name}"
    if language == "go":
        return f"https://pkg.go.dev/{name}"
    return None


def build_heuristic_risk(name: str, language: str) -> dict:
    normalized = name.lower()

    if normalized in STD_LIBS.get(language, set()):
        return {
            "riskLevel": "low",
            "score": 0.05,
            "summary": "Standard library module; not a third-party package.",
            "metadataUrl": registry_url_for(name, language),
        }

    if language == "python":
        signals = extract_pypi_signals(normalized)
    elif language == "javascript":
        signals = extract_npm_signals(normalized)
    elif language == "rust":
        signals = extract_crates_signals(normalized)
    elif language == "go":
        signals = extract_go_signals(normalized)
    else:
        signals = {"exists": False}

    if not signals.get("exists"):
        return {
            "riskLevel": "high",
            "score": 0.9,
            "summary": "Package not found in registry.",
            "metadataUrl": registry_url_for(name, language),
        }

    # Popularity based on downloads/release count
    popularity_risk = 0.5
    weekly_downloads = signals.get("weeklyDownloads")
    download_count = signals.get("downloadCount")
    release_count = signals.get("releaseCount")
    if isinstance(weekly_downloads, (int, float)):
        if weekly_downloads < 100:
            popularity_risk = 0.8
        elif weekly_downloads < 1000:
            popularity_risk = 0.6
        else:
            popularity_risk = 0.2
    elif isinstance(download_count, (int, float)):
        if download_count < 1000:
            popularity_risk = 0.7
        elif download_count < 10000:
            popularity_risk = 0.5
        else:
            popularity_risk = 0.2
    elif release_count is not None:
        if release_count <= 1:
            popularity_risk = 0.7
        elif release_count < 5:
            popularity_risk = 0.5
        else:
            popularity_risk = 0.3

    # Freshness
    freshness_risk = 0.3
    days_first = days_since(signals.get("firstRelease"))
    days_last = days_since(signals.get("lastRelease"))
    if days_first is not None and days_first < 14:
        freshness_risk = 0.7
    elif days_last is not None and days_last < 14:
        freshness_risk = 0.6
    elif days_last is not None and days_last > 365:
        freshness_risk = 0.5

    name_risk = compute_name_risk(normalized)

    maintainer_risk = 0.5
    if signals.get("hasRepo") or signals.get("hasLicense"):
        maintainer_risk = 0.3

    install_risk = 0.2
    if signals.get("hasInstallScripts"):
        install_risk = 0.7
    if signals.get("hasOnlyWheels"):
        install_risk = max(install_risk, 0.6)

    raw_score = (
        1.0 * 0  # existenceRisk is zero here because non-existence short-circuited above
        + 0.9 * name_risk
        + 0.6 * freshness_risk
        + 0.5 * popularity_risk
        + 0.4 * maintainer_risk
        + 0.6 * install_risk
        - 0.3 * (1 if signals.get("hasRepo") else 0)
        - 0.1 * (1 if signals.get("hasLicense") else 0)
    )

    score = clamp(raw_score / 3)
    risk_level = score_to_level(score)

    summary_parts = []
    if name_risk > 0.5:
        summary_parts.append("Name resembles risky patterns.")
    if popularity_risk >= 0.6:
        summary_parts.append("Low adoption or few releases.")
    if freshness_risk >= 0.6:
        summary_parts.append("Very new or recently changed.")
    if install_risk >= 0.6:
        summary_parts.append("Install hooks or binary-only artifacts.")
    if not signals.get("hasRepo") and not signals.get("hasLicense"):
        summary_parts.append("Missing repo/homepage/license metadata.")

    summary = " ".join(summary_parts) or "No strong red flags detected; verify before use."

    return {
        "riskLevel": risk_level,
        "score": score,
        "summary": summary,
        "metadataUrl": registry_url_for(name, language),
    }


def main() -> int:
    """Main entry point for `slopspotter`."""
    logging.debug("starting __main__.main()")
    parser = argparse.ArgumentParser(
        prog="slopspotter",
        description=metadata("slopspotter")["Summary"],
    )
    parser.add_argument(
        "manifest_path",
        nargs="?",
        default="",
        help="The complete path to the app manifest (generated by the extension).",
    )
    parser.add_argument(
        "browser_settings",
        nargs="?",
        default="",
        help="The extension's ID (generated by the extension).",
    )
    parser.add_argument(
        "-i",
        "--install-manifests",
        choices=SUPPORTED_BROWSERS,
        help="Set up the native host to work with the given browser.",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="store_true",
        help="Print the current version and exit.",
    )
    args = parser.parse_args(sys.argv[1:])

    if args.version:
        print(SLOPSPOTTER_VERSION)
        return 0

    if args.install_manifests:
        manifests.install_manifests(args.install_manifests)
        return 0

    if args.manifest_path == "" or args.browser_settings == "":
        print(
            f"Invalid manifest path or settings:"
            f"\n\t- '{args.manifest_path}'"
            f"\n\t- '{args.browser_settings}'"
            "\nSee `slopspotter --help` for more information"
        )
        return 1

    logging.debug("starting loop")
    return loop()


if __name__ == "__main__":
    sys.exit(main())
