"""Tools for installing native messaging manifests in Firefox.

See Also:
    https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/Native_manifests
"""

import json
import os
import shutil
import sys
from importlib.metadata import metadata

from slopspotter import constants

MANIFEST = {
    "name": constants.NATIVE_TO_BACKGROUND_PORT,
    "description": metadata("slopspotter")["Summary"],
    "path": shutil.which("slopspotter"),
    "type": "stdio",
    "allowed_extensions": [constants.ADDON_ID],
}


def get_manifest_paths(local: bool = True):
    """Return the location of the manifests for this operating system.

    Args:
        local: Whether to return the user's manifest paths or global manifest paths.

    See Also:
        https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/Native_manifests
    """
    if not local:
        raise NotImplementedError("Installing manifests globally is not recommended")

    if sys.platform == "linux":
        var_paths = [
            os.path.join(
                "$HOME", ".mozilla", "native-messaging-hosts", "slopspotter.json"
            ),
            os.path.join("$HOME", ".mozilla", "pksc11-modules", "slopspotter.json"),
            os.path.join("$HOME", ".mozilla", "managed-storage", "slopspotter.json"),
        ]
    elif sys.platform == "darwin":
        var_paths = [
            os.path.join(
                "$HOME",
                "Library",
                "Application Support",
                "Mozilla",
                "NativeMessagingHosts",
                "slopspotter.json",
            ),
            os.path.join(
                "$HOME",
                "Library",
                "Application Support",
                "Mozilla",
                "ManagedStorage",
                "slopspotter.json",
            ),
            os.path.join(
                "$HOME",
                "Library",
                "Application Support",
                "Mozilla",
                "PKSC11Modules",
                "slopspotter.json",
            ),
        ]
    else:
        raise NotImplementedError(f"Not implemented on platform {sys.platform}")

    return [os.path.expandvars(path) for path in var_paths]


def install_manifests():
    """Install the manifests to the user's local directory."""
    print("Manifest:", MANIFEST)
    manifest_paths = get_manifest_paths(local=True)
    for manifest_path in manifest_paths:
        print(manifest_path)
        os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
        with open(manifest_path, "w") as file:
            json.dump(MANIFEST, file, indent=4)
