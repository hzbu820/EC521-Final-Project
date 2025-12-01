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


# TODO @vsmercola: Finish integrating changes from @hzbu0820
#
# def loop() -> int:
#     """Main background function."""
#     send_message(encode_message("test"))
#     while True:
#         received_message = get_message()
#         if received_message == "ping":
#             logging.debug("received ping, sending pong")
#             send_message(encode_message("pong"))
#             continue

#         # Command envelope from extension
#         if isinstance(received_message, dict) and "type" in received_message:
#             cmd_type = received_message.get("type")
#             if cmd_type == "check-packages":
#                 logging.debug("received check-packages command")
#                 try:
#                     response = handle_check_packages(received_message.get("payload", {}))
#                     send_message(encode_message(response))
#                 except Exception as exc:  # noqa: BLE001
#                     logging.exception("failed to handle check-packages: %s", exc)
#                     send_message(encode_message({"error": "backend-scoring-error"}))
#                 continue

#         # Unknown message; ignore to allow fallback on the frontend.
#         continue
#     return 0


def handle_check_packages(payload: dict) -> dict:
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
        formatted.append(
            {
                "name": name,
                "language": language,
                "result": {
                    "riskLevel": "unknown",
                    "score": None,
                    "summary": "Backend scoring not implemented; please verify manually.",
                    "metadataUrl": pkg.get("metadataUrl"),
                },
            }
        )

    return {
        "snippetId": snippet_id,
        "packages": formatted,
        "warning": "Backend scoring placeholder in native host.",
    }
