"""Constants & type annotations for the slopspotter package."""

import os
import shutil
from importlib.metadata import metadata
from typing import Any, Literal

ADDON_ID = "slopspotter@bu.edu"
"""Manifest Addon ID."""

NATIVE_TO_BACKGROUND_PORT = "slopspotter"
"""Name of the native port for backend-to-frontend communication."""

SLOPSPOTTER_VERSION = metadata("slopspotter")["Version"]
"""Version number of this package, stored in this project's metadata."""

SUPPORTED_BROWSERS: set[str] = {
    "firefox",
}

SupportedBrowser = Literal["firefox"]

SUPPORTED_PLATFORMS: set[str] = {
    "darwin",
    "linux",
    "win32",
}
"""Set of all supported OS platforms."""

SupportedPlatform = Literal["darwin", "linux", "win32"]
"""Supported OS platforms."""

EXECUTABLE_PATH = shutil.which("slopspotter")
"""Executable path of this application."""

MANIFEST_JSONS: dict[SupportedBrowser, dict[str, Any]] = {
    "firefox": {
        "name": NATIVE_TO_BACKGROUND_PORT,
        "description": metadata("slopspotter")["Summary"],
        "path": EXECUTABLE_PATH,
        "type": "stdio",
        "allowed_extensions": [ADDON_ID],
    }
}
"""Manifest dictionary definitions, sorted by browser."""

UNIXLIKE_MANIFEST_SETTINGS: dict[
    SupportedBrowser, dict[SupportedPlatform, dict[str, Any]]
] = {
    "firefox": {
        "darwin": {
            "global_config": os.path.join(
                "/", "Library", "Application Support", "Mozilla"
            ),
            "local_config": os.path.join(
                "$HOME", "Library", "Application Support", "Mozilla"
            ),
            "json_paths": [
                os.path.join("NativeMessagingHosts", "slopspotter.json"),
                os.path.join("ManagedStorage", "slopspotter.json"),
                os.path.join("PKCS11Modules", "slopspotter.json"),
            ],
        },
        "linux": {
            "global_config": os.path.join("/", "usr", "lib64", "mozilla"),
            "local_config": os.path.join("$HOME", ".mozilla"),
            "json_paths": [
                os.path.join("native-messaging-hosts", "slopspotter.json"),
                os.path.join("managed-storage", "slopspotter.json"),
                os.path.join("pkcs11-modules", "slopspotter.json"),
            ],
        },
    },
}
"""This program's manifest JSON file locations for UNIX-like OSes, sorted by browser/OS.

See also https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/Native_manifests#manifest_location 
"""

WINDOWS_REGISTRY_SUBKEYS: dict[SupportedBrowser, list[str]] = {
    "firefox": [
        r"SOFTWARE\Mozilla\NativeMessagingHosts\slopspotter",
        r"SOFTWARE\Mozilla\ManagedStorage\slopspotter",
        r"SOFTWARE\Mozilla\PKCS11Modules\slopspotter",
    ]
}
"""This program's Windows registry subkeys, sorted by browser.

See also https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/Native_manifests#windows
"""

HF_INSTRUCT_MODELS: set[str] = {
    "Qwen/Qwen2.5-Coder-0.5B-Instruct",
    "Qwen/Qwen2.5-Coder-1.5B-Instruct",
    "Qwen/Qwen2.5-Coder-3B-Instruct",
    "Microsoft/Phi-3-mini-4k-instruct",
    "Microsoft/Phi-3.5-mini-instruct",
    "Microsoft/Phi-4-mini-instruct",
}
"""HuggingFace Instruct LLM model repositories for decision tree analysis."""

FrontendQuestion = dict[Literal["snippetId", "packages"], Any]
"""The content of a native messaging packet sent by the frontend."""

BackendResponse = dict[Literal["snippetId", "packages", "warning"], Any]
"""The content of a native messaging packet sent by the backend."""
