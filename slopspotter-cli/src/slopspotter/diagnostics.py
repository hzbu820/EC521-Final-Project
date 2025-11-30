"""Functions for reporting a package's information."""

from slopspotter.constants import BackendResponse, FrontendQuestion


def placeholder_response(fq: FrontendQuestion) -> BackendResponse:
    """Create a placeholder response from the given frontend question."""
    return {
        "snippetId": fq["snippetId"],
        "packages": [
            {
                "name": fq_package["name"],
                "language": fq_package["language"],
                "result": {
                    "riskLevel": "low",
                    "score": 0.12,
                    "summary": "Lorem ipsum dolor sit amet",
                    "metadataUrl": "https://www.example.com",
                },
            }
            for fq_package in fq["packages"]
        ],
        "warning": "Lorem ipsum dolor sit amet",
    }
