"""Constants for the slopspotter package."""

import os
import shutil
from importlib.metadata import metadata
from typing import Any, Literal

ADDON_ID = "slopspotter@bu.edu"
NATIVE_TO_BACKGROUND_PORT = "slopspotter"

SLOPSPOTTER_VERSION = metadata("slopspotter")["Version"]

SUPPORTED_BROWSERS = [
    "firefox",
]

SUPPORTED_PLATFORMS = [
    "darwin",
    "linux",
    "win32",
]

SupportedBrowser = Literal[*SUPPORTED_BROWSERS]
SupportedPlatform = Literal[*SUPPORTED_PLATFORMS]

EXECUTABLE_PATH = shutil.which("slopspotter")

MANIFEST_JSONS: dict[SupportedBrowser, dict[str, Any]] = {
    "firefox": {
        "name": NATIVE_TO_BACKGROUND_PORT,
        "description": metadata("slopspotter")["Summary"],
        "path": EXECUTABLE_PATH,
        "type": "stdio",
        "allowed_extensions": [ADDON_ID],
    }
}

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

WINDOWS_REGISTRY_SUBKEYS: dict[SupportedBrowser, list[str]] = {
    "firefox": [
        r"SOFTWARE\Mozilla\NativeMessagingHosts\slopspotter",
        r"SOFTWARE\Mozilla\ManagedStorage\slopspotter",
        r"SOFTWARE\Mozilla\PKCS11Modules\slopspotter",
    ]
}
