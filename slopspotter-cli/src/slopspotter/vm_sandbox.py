"""VM Sandbox integration for deep package analysis."""

import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Optional

logger = logging.getLogger(__name__)

# Check if we're on a platform that supports VM sandboxing
VM_SANDBOX_AVAILABLE = sys.platform in ("linux", "darwin")


@dataclass
class VMScanResult:
    """Result of a VM-based package scan."""

    package_name: str
    language: str
    is_malicious: bool
    confidence: float
    indicators: list[str] = field(default_factory=list)
    network_connections: list[Any] = field(default_factory=list)
    file_operations: list[Any] = field(default_factory=list)
    process_spawns: list[Any] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "packageName": self.package_name,
            "language": self.language,
            "isMalicious": self.is_malicious,
            "confidence": self.confidence,
            "indicators": self.indicators,
            "networkConnections": self.network_connections,
            "fileOperations": self.file_operations,
            "processSpawns": self.process_spawns,
            "error": self.error,
        }


def check_vm_requirements() -> tuple[bool, str]:
    if sys.platform == "win32":
        return False, "VM sandbox requires Linux or macOS (WSL not supported)"

    try:
        result = subprocess.run(["which", "qemu-system-x86_64"], capture_output=True, text=True)
        if result.returncode != 0:
            return False, "QEMU not installed. Install with: sudo apt install qemu-system-x86"
    except FileNotFoundError:
        return False, "QEMU not installed"

    try:
        result = subprocess.run(["which", "virsh"], capture_output=True, text=True)
        if result.returncode != 0:
            return False, "libvirt not installed. Install with: sudo apt install libvirt-daemon-system"
    except FileNotFoundError:
        return False, "libvirt not installed"

    return True, "VM sandbox ready"


def get_default_vm_image_path() -> Optional[Path]:
    possible_paths = [
        Path.home() / "slopspotter-vm-images" / "slopspotter-ubuntu-base.qcow2",
        Path.home() / ".slopspotter" / "vm-images" / "slopspotter-ubuntu-base.qcow2",
        Path("/var/lib/slopspotter/vm-images/slopspotter-ubuntu-base.qcow2"),
    ]
    for path in possible_paths:
        if path.exists():
            return path
    return None


def _docker_available() -> bool:
    try:
        proc = subprocess.run(["docker", "version"], capture_output=True, text=True, timeout=3)
        return proc.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _parse_network(lines: list[str], limit: int = 10) -> list[str]:
    return [line.strip()[:220] for line in lines[:limit]]


def _filter_meaningful_network(lines: list[str]) -> list[str]:
    """Filter out network attempts that are clearly blocked (e.g., ENETUNREACH)."""
    signals = []
    for line in lines:
        if any(err in line for err in ("ENETUNREACH", "EAI_AGAIN", "ENOENT")):
            continue
        signals.append(line)
    return signals


def _classify_network(lines: list[str]) -> tuple[int, int]:
    """Classify network connections into benign (known registry/CDN) vs other."""
    benign = 0
    other = 0
    for line in lines:
        # crude match on known registry/CDN patterns
        if any(
            token in line
            for token in (
                "151.101.",  # fastly (pypi/npm)
                "104.16.",  # cloudflare npm
                "104.17.",
                "104.18.",
                "104.19.",
                "104.20.",
                "104.21.",
                "pypi",
                "pythonhosted",
                "npmjs",
                "registry.npmjs",
                "fastly",
                "cloudflare",
                "amazonaws",
                "pkg.github.com",
            )
        ):
            benign += 1
        else:
            other += 1
    return benign, other


def _summarize_endpoints(lines: list[str], max_items: int = 3) -> str:
    """Extract a short summary of unique endpoints from connect() lines."""
    endpoints: list[str] = []
    seen = set()
    for line in lines:
        parts = line.split("inet_addr(\"")
        if len(parts) > 1:
            addr_part = parts[1].split("\")")[0]
            if addr_part and addr_part not in seen:
                seen.add(addr_part)
                endpoints.append(addr_part)
        if len(endpoints) >= max_items:
            break
    if not endpoints:
        return ""
    return ", ".join(endpoints)


def _endpoint_list(lines: list[str], max_items: int = 3) -> list[str]:
    """Return a list of up to max_items unique endpoints from connect() lines."""
    endpoints: list[str] = []
    seen = set()
    for line in lines:
        parts = line.split("inet_addr(\"")
        if len(parts) > 1:
            addr_part = parts[1].split("\")")[0]
            if addr_part and addr_part not in seen:
                seen.add(addr_part)
                endpoints.append(addr_part)
        if len(endpoints) >= max_items:
            break
    return endpoints


def _score_from_signals(
    *,
    prior_risk: str,
    prior_score: Any,
    install_fail: bool,
    timeout: bool,
    container_nonzero: bool,
    net_count: int,
    proc_count: int,
    benign_net: int = 0,
    other_net: int = 0,
    inconclusive: bool = False,
) -> tuple[bool, float]:
    """Compute malicious flag and confidence from sandbox + heuristic signals."""
    prior_low = prior_risk == "low" or (isinstance(prior_score, (int, float)) and prior_score < 0.2)
    prior_high = prior_risk == "high" or (isinstance(prior_score, (int, float)) and prior_score >= 0.7)

    score = 0.05
    if prior_high:
        score += 0.3
    elif isinstance(prior_score, (int, float)) and prior_score >= 0.4:
        score += 0.15

    if timeout:
        score += 0.25
    if install_fail:
        score += 0.2
    if container_nonzero:
        score += 0.1

    score += min(0.3, 0.04 * max(0, net_count))  # cap impact from network count
    # discount benign registry connects
    score -= min(0.1, 0.01 * benign_net)
    score += min(0.2, 0.05 * max(0, other_net))

    if proc_count > 5:
        score += 0.1
    elif proc_count > 1:
        score += 0.05

    if inconclusive:
        score = min(score, 0.45)

    score = min(1.0, max(0.0, score))

    is_malicious = score >= 0.55 or (prior_high and (install_fail or net_count > 0 or timeout))
    if prior_low and score < 0.5:
        is_malicious = False

    # Explicit benign override for clean low-risk runs with only registry traffic
    if prior_low and not install_fail and not timeout and not container_nonzero and other_net <= 2:
        is_malicious = False
        score = min(score, 0.4)

    confidence = min(1.0, max(0.3, score + (0.1 if score > 0.6 else 0.0)))
    return is_malicious, confidence


def _docker_scan_python(package_name: str, context: dict[str, Any]) -> VMScanResult:
    """Scan Python package using the instrumented Docker image."""
    try:
        t0 = time.monotonic()
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                # Allow network so install/import can fetch real artifacts
                "slopspotter-scan-py",
                package_name,
            ],
            capture_output=True,
            text=True,
            timeout=70,
        )
        elapsed = time.monotonic() - t0

        data: dict[str, Any] = {}
        if result.stdout:
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError:
                data = {"install_error": "invalid_json"}

        indicators = ["Docker sandbox (Python)"]
        prior_risk = (context.get("riskLevel") or "").lower()
        prior_score = context.get("score")

        meaningful_net = _filter_meaningful_network(data.get("network", []))
        net_count = len(meaningful_net)
        benign_net, other_net = _classify_network(meaningful_net)
        endpoint_summary = _summarize_endpoints(meaningful_net)
        install_version = data.get("installed_version")
        download_bytes = data.get("download_bytes")
        proc_count = len(data.get("processes", []))
        install_fail = bool(
            data.get("install_error") or data.get("import_error") or (data.get("install_rc") not in (0, None)) or (data.get("import_rc") not in (0, None))
        )
        timeout = bool(data.get("timeout"))
        container_nonzero = result.returncode != 0
        inconclusive = install_fail and not meaningful_net and prior_risk == "low"
        endpoints = _endpoint_list(meaningful_net)

        if container_nonzero:
            indicators.append("Sandbox container returned non-zero status")
        if timeout:
            indicators.append("Sandbox timeout during install/import")
        if data.get("install_error") or data.get("import_error") or install_fail:
            indicators.append("Install/import failed inside sandbox")
        if meaningful_net:
            indicators.append("Network attempts observed")
        if install_fail and not (data.get("install_error") or data.get("import_error")):
            indicators.append("Install/import reported non-zero status")
        if benign_net and not other_net:
            indicators.append(f"Registry/CDN connects: {benign_net}")
        if other_net:
            indicators.append(f"Non-registry connects: {other_net}")
        if endpoint_summary:
            indicators.append(f"Endpoints: {endpoint_summary}")
        if install_version:
            indicators.append(f"Installed version: {install_version}")
        if download_bytes:
            indicators.append(f"Downloaded: {download_bytes} bytes")
        if elapsed:
            indicators.append(f"Elapsed: {elapsed:.1f}s")

        is_malicious, confidence = _score_from_signals(
            prior_risk=prior_risk,
            prior_score=prior_score,
            install_fail=install_fail,
            timeout=timeout,
            container_nonzero=container_nonzero,
            net_count=net_count,
            proc_count=proc_count,
            benign_net=benign_net,
            other_net=other_net,
            inconclusive=inconclusive,
        )

        return VMScanResult(
            package_name=package_name,
            language="Python",
            is_malicious=is_malicious,
            confidence=confidence,
            indicators=indicators,
            network_connections=endpoints,
            file_operations=[],
            process_spawns=_parse_network(data.get("processes", [])),
        )

    except subprocess.TimeoutExpired:
        return VMScanResult(
            package_name=package_name,
            language="Python",
            is_malicious=True,
            confidence=0.75,
            indicators=["Sandbox timeout during install/import", "Docker sandbox (Python)"],
            network_connections=[],
            file_operations=[],
            process_spawns=[],
        )
    except Exception as e:  # pragma: no cover
        return VMScanResult(
            package_name=package_name,
            language="Python",
            is_malicious=False,
            confidence=0.0,
            error=str(e),
        )


def _docker_scan_npm(package_name: str, context: dict[str, Any]) -> VMScanResult:
    """Scan NPM package using the instrumented Docker image."""
    try:
        t0 = time.monotonic()
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                # Allow network so install/require can fetch real artifacts
                "slopspotter-scan-node",
                package_name,
            ],
            capture_output=True,
            text=True,
            timeout=70,
        )
        elapsed = time.monotonic() - t0

        data: dict[str, Any] = {}
        if result.stdout:
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError:
                data = {"install_error": "invalid_json"}

        prior_risk = (context.get("riskLevel") or "").lower()
        prior_score = context.get("score")

        meaningful_net = _filter_meaningful_network(data.get("network", []))
        net_count = len(meaningful_net)
        benign_net, other_net = _classify_network(meaningful_net)
        endpoint_summary = _summarize_endpoints(meaningful_net)
        endpoints = _endpoint_list(meaningful_net)
        install_version = data.get("installed_version")
        download_bytes = data.get("download_bytes")
        proc_count = len(data.get("processes", []))
        install_fail = bool(
            data.get("install_error") or data.get("require_error") or (data.get("install_rc") not in (0, None)) or (data.get("require_rc") not in (0, None))
        )
        timeout = bool(data.get("timeout"))
        container_nonzero = result.returncode != 0
        inconclusive = install_fail and not meaningful_net and prior_risk == "low"

        orig_lang = (context.get("originalLanguage") or "").lower()
        label_lang = "TypeScript" if orig_lang in ("ts", "typescript") else "JavaScript"
        indicators = [f"Docker sandbox ({label_lang})"]
        if container_nonzero:
            indicators.append("Sandbox container returned non-zero status")
        if timeout:
            indicators.append("Sandbox timeout during install/require")
        if data.get("install_error") or data.get("require_error") or install_fail:
            indicators.append("Install/require failed inside sandbox")
        if meaningful_net:
            indicators.append("Network attempts observed")
        if install_fail and not (data.get("install_error") or data.get("require_error")):
            indicators.append("Install/require reported non-zero status")
        if benign_net and not other_net:
            indicators.append(f"Registry/CDN connects: {benign_net}")
        if other_net:
            indicators.append(f"Non-registry connects: {other_net}")
        if endpoint_summary:
            indicators.append(f"Endpoints: {endpoint_summary}")
        if install_version:
            indicators.append(f"Installed version: {install_version}")
        if download_bytes:
            indicators.append(f"Downloaded: {download_bytes} bytes")
        if elapsed:
            indicators.append(f"Elapsed: {elapsed:.1f}s")

        is_malicious, confidence = _score_from_signals(
            prior_risk=prior_risk,
            prior_score=prior_score,
            install_fail=install_fail,
            timeout=timeout,
            container_nonzero=container_nonzero,
            net_count=net_count,
            proc_count=proc_count,
            benign_net=benign_net,
            other_net=other_net,
            inconclusive=inconclusive,
        )

        return VMScanResult(
            package_name=package_name,
            language="JavaScript",
            is_malicious=is_malicious,
            confidence=confidence,
            indicators=indicators,
            network_connections=endpoints,
            file_operations=[],
            process_spawns=_parse_network(data.get("processes", [])),
        )

    except subprocess.TimeoutExpired:
        return VMScanResult(
            package_name=package_name,
            language="JavaScript",
            is_malicious=True,
            confidence=0.75,
            indicators=["Sandbox timeout during install/require", "Docker sandbox (JavaScript)"],
            network_connections=[],
            file_operations=[],
            process_spawns=[],
        )
    except Exception as e:  # pragma: no cover
        return VMScanResult(
            package_name=package_name,
            language="JavaScript",
            is_malicious=False,
            confidence=0.0,
            error=str(e),
        )


def deep_scan_package(
    package_name: str,
    language: Literal["Python", "JavaScript", "Go", "Rust"],
    vm_image_path: Optional[str] = None,
    timeout: int = 120,
    context: Optional[dict[str, Any]] = None,
) -> VMScanResult:
    # Prefer Docker path
    if _docker_available():
        try:
            if language == "Python":
                return _docker_scan_python(package_name, context or {})
            if language == "JavaScript":
                return _docker_scan_npm(package_name, context or {})
            # Go/Rust not yet supported in sandbox; return informative placeholder
            return VMScanResult(
                package_name=package_name,
                language=language,
                is_malicious=False,
                confidence=0.3,
                indicators=[f"Deep scan not available for {language}; using heuristic only."],
                network_connections=[],
                file_operations=[],
                process_spawns=[],
            )
        except Exception as e:  # pragma: no cover
            logger.warning("Docker scan failed, falling back to VM if available: %s", e)

    # VM fallback (rare)
    available, message = check_vm_requirements()
    if not available:
        return VMScanResult(
            package_name=package_name,
            language=language,
            is_malicious=False,
            confidence=0.0,
            error=f"VM sandbox not available: {message}",
        )

    image_path = Path(vm_image_path) if vm_image_path else get_default_vm_image_path()
    if not image_path or not image_path.exists():
        return VMScanResult(
            package_name=package_name,
            language=language,
            is_malicious=False,
            confidence=0.0,
            error="VM image not found. Run vm_image_builder_script.py first.",
        )

    try:
        from slopspotter.vm_sandbox_core import run_vm_scan

        return run_vm_scan(
            package_name=package_name,
            language=language,
            vm_image_path=str(image_path),
            timeout=timeout,
        )
    except Exception as e:  # pragma: no cover
        return VMScanResult(
            package_name=package_name,
            language=language,
            is_malicious=False,
            confidence=0.0,
            error=str(e),
        )


def _lightweight_scan(package_name: str, language: Literal["Python", "JavaScript"], context: Optional[dict[str, Any]] = None) -> VMScanResult:
    if not _docker_available():
        return VMScanResult(
            package_name=package_name,
            language=language,
            is_malicious=False,
            confidence=0.0,
            error="Neither VM nor Docker available for deep scanning",
        )
    if language == "Python":
        return _docker_scan_python(package_name, context or {})
    if language == "JavaScript":
        return _docker_scan_npm(package_name, context or {})
    return VMScanResult(
        package_name=package_name,
        language=language,
        is_malicious=False,
        confidence=0.3,
        indicators=[f"Deep scan not available for {language}; using heuristic only."],
        network_connections=[],
        file_operations=[],
        process_spawns=[],
    )


def handle_deep_scan_request(payload: dict[str, Any]) -> dict[str, Any]:
    package_name = payload.get("packageName", "")
    logger.debug("handle_deep_scan_request: payload=%s", payload)
    logger.debug("handle_deep_scan_request: package_name='%s'", package_name)
    language = payload.get("language", "Python")
    vm_image_path = payload.get("vmImagePath")

    if not package_name:
        return {"success": False, "error": "Package name is required"}

    lang_lower = language.lower()
    if lang_lower in ("python", "py"):
        language = "Python"
    elif lang_lower in ("javascript", "js", "node", "npm", "typescript", "ts"):
        language = "JavaScript"
    elif lang_lower in ("go", "golang"):
        language = "Go"
    elif lang_lower in ("rust", "rs", "cargo"):
        language = "Rust"
    else:
        return {"success": False, "error": f"Unsupported language: {language}"}

    result = deep_scan_package(
        package_name=package_name,
        language=language,
        vm_image_path=vm_image_path,
        context=payload.get("context") or {},
    )

    result_dict = result.to_dict()
    if result_dict.get("error"):
        return {"success": False, "error": result_dict["error"], "result": result_dict}

    return {"success": True, "result": result_dict}
