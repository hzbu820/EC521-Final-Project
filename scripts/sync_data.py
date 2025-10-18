#!/usr/bin/env python3
"""Tools for ensuring data parity between sub-projects.

This file should be run from the project's root directory to ensure constants &
metadata are shared between the `slopspotter-cli` Python project and the
`slopspotter-extension` browser extension.

bash::
    python3 scripts/sync_data.py
"""

import json
import os
import sys
import tomllib
from typing import Dict, List

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Root directory of the project."""

PYPROJECT_FILE = os.path.join(ROOT_DIR, "slopspotter-cli", "pyproject.toml")
"""Location of the Python CLI project's `pyproject.toml` file."""

MANIFEST_FILE = os.path.join(ROOT_DIR, "slopspotter-extension", "manifest.json")
"""Location of the Firefox extension's `manifest.json` file."""


def running_in_scripts_dir():
    """Returns `True` if the script is running from the `scripts` directory."""
    return os.path.basename(os.getcwd()) == "scripts"


def read_pyproject_toml():
    """Open the `pyproject.toml` file and return the data."""
    try:
        with open(PYPROJECT_FILE, "rb") as pyproject_file:
            pyproject_data = tomllib.load(pyproject_file)
    except (FileNotFoundError, tomllib.TOMLDecodeError) as error:
        raise error
    return pyproject_data


def read_manifest_json():
    """Open the `manifest.json` file and return the data."""
    try:
        with open(MANIFEST_FILE, "r") as manifest_file:
            manifest_data = json.load(manifest_file)
    except (FileNotFoundError, json.JSONDecodeError) as error:
        raise error
    return manifest_data


def read_constants_json(constants_json_path: str):
    """Open the `constants.json` file at the given path and return the data."""
    try:
        with open(constants_json_path, "r") as file:
            constants = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as error:
        raise error
    return constants


def copy_metadata():
    """Copy metadata from the `slopspotter-cli` Python Project to the `slopspotter-cli` Firefox extension."""
    pyproject_data = read_pyproject_toml()
    manifest_data = read_manifest_json()

    project_meta: Dict = pyproject_data.get("project")
    name: str = project_meta.get("name")
    version: str = project_meta.get("version")
    description: str = project_meta.get("description")
    authors: List[Dict[str, str]] = project_meta.get("authors")
    homepage: str = project_meta.get("urls", {}).get(
        "Repository",
    )

    manifest_data["name"] = name
    manifest_data["version"] = version
    manifest_data["description"] = description
    manifest_data["homepage_url"] = homepage
    manifest_data["author"] = ", ".join(author.get("name") for author in authors)

    with open(MANIFEST_FILE, "w") as manifest_file:
        json.dump(manifest_data, manifest_file, indent=2)


if __name__ == "__main__":
    if running_in_scripts_dir():
        print("This script should be run from the project's root directory.")
        sys.exit(1)

    print(f"Root Directory:\t{ROOT_DIR}")
    print(f"Pyproject File:\t{PYPROJECT_FILE}")
    print(f"Manifest File:\t{MANIFEST_FILE}")

    print("Copying metadata...")
    copy_metadata()
    print("Done!")
    sys.exit(0)
