"""Extract data from PyPI, NPM, and other package registries."""

import json
import urllib.error
import urllib.request
from datetime import datetime

LANGUAGE_ALIASES = {
    "typescript": "javascript",
}


def normalize_language(language: str) -> str:
    return LANGUAGE_ALIASES.get(language, language)


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
    homepage = (
        data.get("info", {}).get("home_page")
        or project_urls.get("Homepage")
        or project_urls.get("home")
    )
    if not homepage:
        homepage = next(
            (url for url in project_urls.values() if isinstance(url, str) and url.strip()),
            None,
        )
    repo = (
        project_urls.get("Source")
        or project_urls.get("Repository")
        or project_urls.get("Code")
        or project_urls.get("source")
        or project_urls.get("GitHub")
        or project_urls.get("gitlab")
    )
    if not repo:
        repo = next(
            (
                url
                for url in project_urls.values()
                if isinstance(url, str)
                and ("github" in url.lower() or "gitlab" in url.lower() or "bitbucket" in url.lower())
            ),
            None,
        )
    license_text = (data.get("info", {}) or {}).get("license") or ""

    return {
        "exists": True,
        "firstRelease": first_release,
        "lastRelease": last_release,
        "releaseCount": len(releases),
        "hasOnlyWheels": has_only_wheels and not has_sdist,
        "homepage": homepage,
        "repo": repo,
        "license": license_text if license_text and "unknown" not in license_text.lower() else "",
        "metadataUrl": registry_url_for(name, "python"),
    }


def extract_npm_signals(name: str) -> dict:
    registry = fetch_json(f"https://registry.npmjs.org/{name}")
    downloads = fetch_json(f"https://api.npmjs.org/downloads/point/last-week/{name}")
    if not registry:
        return {"exists": False}

    time = registry.get("time", {}) or {}
    version_dates = []
    for key, value in time.items():
        if key in ("created", "modified"):
            continue
        if not isinstance(value, str):
            continue
        try:
            version_dates.append(datetime.fromisoformat(value.replace("Z", "+00:00")))
        except ValueError:
            continue
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

    repo = latest_meta.get("repository")
    if isinstance(repo, dict):
        repo = repo.get("url")
    homepage = latest_meta.get("homepage")
    license_field = latest_meta.get("license")
    if isinstance(license_field, dict):
        license_text = license_field.get("type") or license_field.get("name")
    else:
        license_text = license_field
    return {
        "exists": True,
        "firstRelease": first_release,
        "lastRelease": last_release,
        "releaseCount": len(version_dates),
        "hasInstallScripts": has_install_scripts,
        "repo": repo,
        "homepage": homepage,
        "license": license_text,
        "weeklyDownloads": weekly_downloads,
        "metadataUrl": registry_url_for(name, "javascript"),
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
        "repo": crate.get("repository"),
        "homepage": crate.get("homepage"),
        "license": crate.get("license"),
        "metadataUrl": registry_url_for(name, "rust"),
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
                "repo": f"https://pkg.go.dev/{name}" if "." in name else None,
                "metadataUrl": registry_url_for(name, "go"),
            }
    except urllib.error.URLError:
        return {"exists": False}


def registry_url_for(name: str, language: str) -> str | None:
    language = normalize_language(language)
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
    language = normalize_language(language)
    if language == "python":
        return extract_pypi_signals(name)
    if language == "javascript":
        return extract_npm_signals(name)
    if language == "rust":
        return extract_crates_signals(name)
    if language == "go":
        return extract_go_signals(name)
