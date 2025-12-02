"""Extract data from PyPI, NPM, and other package registries."""

import json
import urllib.error
import urllib.request
from datetime import datetime


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
                    dates.append(
                        datetime.fromisoformat(upload_time.replace("Z", "+00:00"))
                    )
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
    has_any_project_url = any(
        isinstance(v, str) and v.strip() for v in project_urls.values()
    )

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
    latest_meta = (
        (registry.get("versions") or {}).get(latest_version, {})
        if latest_version
        else {}
    )
    scripts = latest_meta.get("scripts") or {}
    has_install_scripts = "install" in scripts or "postinstall" in scripts
    weekly_downloads = (
        downloads.get("downloads") if isinstance(downloads, dict) else None
    )

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
    latest_meta = (
        (registry.get("versions") or {}).get(latest_version, {})
        if latest_version
        else {}
    )
    scripts = latest_meta.get("scripts") or {}
    has_install_scripts = "install" in scripts or "postinstall" in scripts
    weekly_downloads = (
        downloads.get("downloads") if isinstance(downloads, dict) else None
    )

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
            first_release = datetime.fromisoformat(
                crate["created_at"].replace("Z", "+00:00")
            )
        except ValueError:
            pass
    if crate.get("updated_at"):
        try:
            last_release = datetime.fromisoformat(
                crate["updated_at"].replace("Z", "+00:00")
            )
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
        with urllib.request.urlopen(
            f"https://proxy.golang.org/{name}/@v/list", timeout=3
        ) as resp:
            if resp.status != 200:
                return {"exists": False}
            versions = [
                line.strip()
                for line in resp.read().decode("utf-8").splitlines()
                if line.strip()
            ]
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


def extract_registry_signals(name: str, language: str):
    if language == "python":
        return extract_pypi_signals(name)
    if language == "javascript":
        return extract_npm_signals(name)
    if language == "rust":
        return extract_crates_signals(name)
    if language == "go":
        return extract_go_signals(name)
