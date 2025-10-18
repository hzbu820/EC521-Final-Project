"""Import the shared constants stored in the `constants.json` file."""

import os
import shutil
from importlib.metadata import metadata
from typing import Any, Dict, Literal

ADDON_ID = "slopspotter@bu.edu"
NATIVE_TO_BACKGROUND_PORT = "slopspotter"

SUPPORTED_BROWSERS = [
    "firefox",
    "chromium",
    "chrome",
]

SUPPORTED_PLATFORMS = [
    "darwin",
    "linux",
]

SupportedBrowser = Literal[*SUPPORTED_BROWSERS]
SupportedPlatform = Literal[*SUPPORTED_PLATFORMS]

FIREFOX_MANIFEST = {
    "name": NATIVE_TO_BACKGROUND_PORT,
    "description": metadata("slopspotter")["Summary"],
    "path": shutil.which("slopspotter"),
    "type": "stdio",
    "allowed_extensions": [ADDON_ID],
}

CHROMIUM_MANIFEST = {
    "name": NATIVE_TO_BACKGROUND_PORT,
    "description": metadata("slopspotter")["Summary"],
    "path": shutil.which("slopspotter"),
    "type": "stdio",
    "allowed_origins": [ADDON_ID],
}

MANIFEST_SETTINGS: Dict[SupportedBrowser, Dict[SupportedPlatform, Dict[str, Any]]] = {
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
    "chrome": {
        "darwin": {
            "global_config": os.path.join("/", "Library", "Google", "Chrome"),
            "local_config": os.path.join(
                "$HOME", "Library", "Application Support", "Google", "Chrome"
            ),
            "json_paths": [
                os.path.join("NativeMessagingHosts", "com.bu.slopspotter.json"),
            ],
        },
        "linux": {
            "global_config": os.path.join("/", "etc", "opt", "chrome"),
            "local_config": os.path.join("$HOME", ".config", "google-chrome"),
            "json_paths": [
                os.path.join("NativeMessagingHosts", "com.bu.slopspotter.json"),
            ],
        },
    },
    "chromium": {
        "darwin": {
            "global_config": os.path.join(
                "/", "Library", "Application Support", "Chromium"
            ),
            "local_config": os.path.join(
                "$HOME", "Library", "Application Support", "Chromium"
            ),
            "json_paths": [
                os.path.join("NativeMessagingHosts", "com.bu.slopspotter.json"),
            ],
        },
        "linux": {
            "global_config": os.path.join("/", "etc", "chromium"),
            "local_config": os.path.join("$HOME", ".config", "chromium"),
            "json_paths": [
                os.path.join("NativeMessagingHosts", "com.bu.slopspotter.json"),
            ],
        },
    },
}
