"""Tools for installing native messaging manifests in Firefox.

https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/Native_manifests
"""

import json
import os
import sys

if sys.platform == "win32":
    import winreg

from slopspotter.constants import (
    EXECUTABLE_PATH,
    MANIFEST_JSONS,
    SUPPORTED_BROWSERS,
    SUPPORTED_PLATFORMS,
    UNIXLIKE_MANIFEST_SETTINGS,
    WINDOWS_REGISTRY_SUBKEYS,
    SupportedBrowser,
)


def get_unixlike_manifest_paths(
    browser: SupportedBrowser, is_local: bool = True
) -> list[str]:
    """Get the manifest paths for the current operating system.

    Windows does not have manifest paths; native manifests are stored in the registry.

    Args:
        browser: The browser to install the manifest for.
        is_local: Whether to install the manifest in the local or global config.

    Raises:
        TypeError: If the platform or browser is not supported.
    """
    if sys.platform == "win32":
        raise TypeError("Windows does not have manifest paths")
    if sys.platform not in SUPPORTED_PLATFORMS:
        raise TypeError(f"Invalid platform: {sys.platform}")

    browser_platform_settings = UNIXLIKE_MANIFEST_SETTINGS[browser][sys.platform]

    config = (
        browser_platform_settings["local_config"]
        if is_local
        else browser_platform_settings["global_config"]
    )
    json_paths = browser_platform_settings["json_paths"]

    return [
        os.path.join(os.path.expandvars(config), json_path) for json_path in json_paths
    ]


def install_manifests(browser: SupportedBrowser, is_local: bool = True) -> None:
    """Install the native app manifest.

    See also ``install_unixlike_manifests``, ``install_win32_manifests`` for
    OS-specific implementations.

    Args:
        browser: The browser to install the manifest for.
        is_local: Whether to install the manifest in the local or global config.

    """
    if sys.platform not in SUPPORTED_PLATFORMS:
        raise TypeError(f"Invalid platform: {sys.platform}")
    if browser not in SUPPORTED_BROWSERS:
        raise ValueError(f"Unsupported Browser: {browser}")

    if sys.platform == "win32":
        install_win32_manifests(browser, is_local)
        return
    install_unixlike_manifests(browser, is_local)


def install_unixlike_manifests(
    browser: SupportedBrowser, is_local: bool = True
) -> None:
    """Install the native app manifest for UNIX-like OSes (MacOS & Linux)."""
    manifest_paths = get_unixlike_manifest_paths(browser, is_local)
    manifest = MANIFEST_JSONS[browser]

    print(f"Manifest: {manifest}")
    for manifest_path in manifest_paths:
        print(f"Storing manifest in {manifest_path}")
        os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
        with open(manifest_path, "w") as manifest_file:
            json.dump(manifest, manifest_file, indent=4)


def install_win32_manifests(browser: SupportedBrowser, is_local: bool = True):
    """Install the manifest in the Windows registry."""
    if sys.platform != "win32":
        raise OSError(f"Cannot install Windows manifest on platform {sys.platform}")

    # On Windows, registry keys point to a manifest.json file on disk.
    manifest_dir = os.path.join(os.path.expandvars(r"%LOCALAPPDATA%"), "slopspotter")
    os.makedirs(manifest_dir, exist_ok=True)
    manifest_path = os.path.join(manifest_dir, "slopspotter.json")

    manifest = MANIFEST_JSONS[browser]
    manifest["path"] = EXECUTABLE_PATH

    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=4)

    key = winreg.HKEY_CURRENT_USER if is_local else winreg.HKEY_LOCAL_MACHINE
    sub_keys = WINDOWS_REGISTRY_SUBKEYS.get(browser, [])

    for sub_key in sub_keys:
        winreg.CreateKey(key, sub_key)
        winreg.SetValue(key, sub_key, winreg.REG_SZ, manifest_path)
