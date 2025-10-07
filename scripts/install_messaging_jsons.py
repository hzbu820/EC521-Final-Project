# Run this from the project root

import json
import os
import shutil

with open("scripts/slopspotter.json", "r") as file:
    slopspotter_manifest = json.load(file)

slopspotter_manifest["path"] = os.path.join(os.getcwd(), "python_app/src/__main__.py")

print("Installing manifest")
print(slopspotter_manifest)

manifest_filenames = [
    f"/home/{os.environ['USER']}/.mozilla/managed-storage/slopspotter.json",
    f"/home/{os.environ['USER']}/.mozilla/pkcs11-modules/slopspotter.json",
    f"/home/{os.environ['USER']}/.mozilla/managed-storage/slopspotter.json",
]

for manifest_fname in manifest_filenames:
    print(manifest_fname)
    with open(manifest_fname, "w") as file:
        json.dump(slopspotter_manifest, file, indent=4)
