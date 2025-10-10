#!/usr/bin/env python
"""Copy metadata between the `slopspotter-cli` Python Project and the `slopspotter-cli` Firefox extension."""

import json
import os
import sys
import tomllib
from typing import Dict, List

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Root directory of the project."""

PYPROJECT_FILE = os.path.join(ROOT_DIR, "slopspotter-cli", "pyproject.toml")
"""Root directory of the Python CLI project."""

MANIFEST_FILE = os.path.join(ROOT_DIR, "slopspotter-extension", "manifest.json")
"""Root directory of the Firefox extension."""

print(f"Root Directory:\t{ROOT_DIR}")
print(f"Pyproject File:\t{PYPROJECT_FILE}")
print(f"Manifest File:\t{MANIFEST_FILE}")

try:
    with open(PYPROJECT_FILE, "rb") as pyproject_file:
        pyproject_data = tomllib.load(pyproject_file)
except FileNotFoundError as error:
    print(f"Error: {error}")
    sys.exit(1)
except tomllib.TOMLDecodeError as error:
    print(f"Error: {error}")
    sys.exit(1)

project_meta: Dict = pyproject_data.get("project")
if project_meta is None:
    print("Error: no project metadata found in pyproject.toml")
    sys.exit(1)

name: str = project_meta.get("name")
if name is None:
    print("Error: no project name found in pyproject.toml")
    sys.exit(1)

version: str = project_meta.get("version")
if version is None:
    print("Error: no project version found in pyproject.toml")
    sys.exit(1)

description: str = project_meta.get("description")
if description is None:
    print("Error: no project description found in pyproject.toml")
    sys.exit(1)

authors: List[Dict[str, str]] = project_meta.get("authors")
if authors is None:
    print("Error: no project authors found in pyproject.toml")
    sys.exit(1)

homepage: str = project_meta.get("urls", {}).get("Repository", "")
if homepage is None:
    print("Error: no project homepage found in pyproject.toml")
    sys.exit(1)

try:
    with open(MANIFEST_FILE, "r") as manifest_file:
        manifest_data = json.load(manifest_file)
except FileNotFoundError as error:
    print(f"Error: {error}")
    sys.exit(1)
except json.JSONDecodeError as error:
    print(f"Error: {error}")
    sys.exit(1)

manifest_data["name"] = name
manifest_data["version"] = version
manifest_data["description"] = description
manifest_data["homepage_url"] = homepage
manifest_data["author"] = ", ".join(author.get("name") for author in authors)

print(manifest_data)

with open(MANIFEST_FILE, "w") as manifest_file:
    json.dump(manifest_data, manifest_file, indent=2)

sys.exit(0)
