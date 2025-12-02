"""Functions for reporting a package's information."""

from slopspotter.constants import BackendResponse, FrontendQuestion
from slopspotter.scoring import score_package


def handle_check_packages(payload: FrontendQuestion) -> BackendResponse:
    """Build a structured response for check-packages command.

    Placeholder scorer: returns "unknown" risk so the pipeline remains wired.
    Replace this with a real classifier to override the frontend heuristic.
    """
    snippet_id = payload.get("snippetId", "")
    packages = payload.get("packages", []) or []

    formatted = []
    for pkg in packages:
        name = pkg.get("name", "")
        language = pkg.get("language", "")
        meta = pkg.get("meta") or {}
        pkg_score = score_package(name=name, language=language, meta=meta)
        formatted.append(
            {
                "name": name,
                "language": language,
                "result": {
                    "riskLevel": pkg_score.riskLevel,
                    "score": pkg_score.score,
                    "summary": pkg_score.summary,
                    "metadataUrl": pkg_score.metadataUrl,
                    "signals": pkg_score.signals,
                },
            }
        )

    return {
        "snippetId": snippet_id,
        "packages": formatted,
        "warning": None,
    }
