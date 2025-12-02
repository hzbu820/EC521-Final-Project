"""Primitive risk signal helpers used by the scorer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

NAME_TOKENS = ["installer", "updater", "crypto", "mining", "hack", "typo"]

PYTHON_STDLIB = {
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
    "os",
    "pathlib",
    "pickle",
    "platform",
    "plistlib",
    "queue",
    "random",
    "re",
    "sched",
    "secrets",
    "shutil",
    "signal",
    "socket",
    "sqlite3",
    "ssl",
    "statistics",
    "string",
    "subprocess",
    "sys",
    "tempfile",
    "textwrap",
    "threading",
    "time",
    "typing",
    "uuid",
    "xml",
    "zipfile",
}

GO_STDLIB = {
    "fmt",
    "http",
    "net/http",
    "strings",
    "io",
    "os",
    "math",
    "time",
    "bytes",
    "crypto",
}

RUST_STDLIB = {
    "std",
}


@dataclass
class SignalResult:
    """Represents an individual signal score and a short reason."""

    score: float
    reason: str


def stdlib_allowlist(name: str, language: str) -> SignalResult | None:
    """Return a low-risk override if a package is a known stdlib module."""
    lowered = (name or "").strip().lower()
    lang = (language or "").strip().lower()
    if lang == "python" and lowered in PYTHON_STDLIB:
        return SignalResult(0.0, "Python stdlib module")
    if lang == "go" and lowered in GO_STDLIB:
        return SignalResult(0.0, "Go stdlib package")
    if lang == "rust" and lowered in RUST_STDLIB:
        return SignalResult(0.0, "Rust stdlib crate")
    return None


def name_signal(name: str) -> SignalResult:
    """Simple lexical risk: suspicious tokens, digits/hyphens, length."""
    lowered = (name or "").lower()
    if not lowered:
        return SignalResult(0.4, "Missing name")

    risk = 0.0
    reasons: list[str] = []

    if any(token in lowered for token in NAME_TOKENS):
        risk += 0.4
        reasons.append("Suspicious token")
    if any(char.isdigit() for char in lowered):
        risk += 0.2
        reasons.append("Contains digits")
    if "-" in lowered:
        risk += 0.1
        reasons.append("Contains hyphen")
    if len(lowered) > 30:
        risk += 0.1
        reasons.append("Long name")

    return SignalResult(min(risk, 1.0), ", ".join(reasons) or "Benign name")


def registry_signal(meta: dict[str, Any] | None) -> SignalResult:
    """Registry presence and freshness if provided."""
    if not meta:
        return SignalResult(0.3, "No registry metadata")
    if meta.get("exists") is False:
        return SignalResult(1.0, "Package not found in registry")
    return SignalResult(0.0, "Found in registry")


def install_signal(meta: dict[str, Any] | None) -> SignalResult:
    """Install-time risk: npm scripts or wheels-only."""
    if not meta:
        return SignalResult(0.0, "No install flags")
    if meta.get("hasInstallScripts"):
        return SignalResult(0.6, "Installs with scripts")
    if meta.get("wheelsOnly"):
        return SignalResult(0.3, "Wheels only (no sdist)")
    return SignalResult(0.0, "No install concerns")


def metadata_signal(meta: dict[str, Any] | None) -> SignalResult:
    """Metadata completeness: repo/homepage/license."""
    if not meta:
        return SignalResult(0.3, "Missing metadata")
    missing = []
    if not meta.get("repo"):
        missing.append("repo")
    if not meta.get("homepage"):
        missing.append("homepage")
    if not meta.get("license"):
        missing.append("license")
    if missing:
        return SignalResult(0.3, f"Missing {', '.join(missing)}")
    return SignalResult(0.0, "Metadata present")
