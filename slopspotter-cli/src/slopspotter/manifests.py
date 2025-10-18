"""Tools for installing native messaging manifests in Firefox.

See Also:
    https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/Native_manifests
"""

import json
import os
import sys

from slopspotter.constants import (
    CHROMIUM_MANIFEST,
    FIREFOX_MANIFEST,
    MANIFEST_SETTINGS,
    SUPPORTED_BROWSERS,
)


def get_manifest_paths(browser: str, is_local: bool = True):
    browser_settings = MANIFEST_SETTINGS.get(browser, {})
    if not browser_settings:
        raise TypeError(f"Invalid browser: {browser}")
    browser_platform_settings = browser_settings.get(sys.platform, {})
    if not browser_platform_settings:
        raise TypeError(f"Invalid platform: {sys.platform}")

    config = (
        browser_platform_settings["local_config"]
        if is_local
        else browser_platform_settings["global_config"]
    )
    json_paths = browser_platform_settings["json_paths"]

    return [
        os.path.join(os.path.expandvars(config), json_path) for json_path in json_paths
    ]


def install_manifests(browser: str, is_local: bool = True):
    if browser not in SUPPORTED_BROWSERS:
        raise ValueError(f"Unsupported Browser: {browser}")

    manifest_paths = get_manifest_paths(browser, is_local)
    manifest = FIREFOX_MANIFEST if browser == "firefox" else CHROMIUM_MANIFEST

    print(f"Manifest: {manifest}")
    for manifest_path in manifest_paths:
        print(f"Storing manifest in {manifest_path}")
        os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
        with open(manifest_path, "w") as manifest_file:
            json.dump(manifest, manifest_file, indent=4)
