"""Import the shared constants stored in the `constants.json` file."""

import json
import os

import slopspotter

CONSTANTS_JSON = os.path.join(os.path.dirname(slopspotter.__file__), "constants.json")

with open(CONSTANTS_JSON, "r") as f:
    constants = json.load(f)

ADDON_ID = constants["browser_specific_settings"]["gecko"]["id"]
NATIVE_TO_BACKGROUND_PORT = constants["nativeToBackgroundPort"]
