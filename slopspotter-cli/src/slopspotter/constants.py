"""Import the shared constants stored in the `constants.json` file."""

import json
import os

with open(os.path.join(os.path.dirname(__file__), "constants.json")) as f:
    constants = json.load(f)

ADDON_ID = constants["browser_specific_settings"]["gecko"]["id"]
