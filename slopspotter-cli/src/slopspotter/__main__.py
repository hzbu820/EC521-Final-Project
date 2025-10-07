import argparse
import json
import os
import stat


MANIFEST = {
    "name": "slopspotter",
    "description": "Get info about a package suggested by an AI language model",
    "path": os.path.join(os.path.dirname(__file__), "main_host.py"),
    "type": "stdio",
    "allowed_extensions": ["ping_pong@example.org"],
}

manifest_fnames = [
    f"/home/{os.environ['USER']}/.mozilla/native-messaging-hosts/slopspotter.json",
    f"/home/{os.environ['USER']}/.mozilla/pkcs11-modules/slopspotter.json",
    f"/home/{os.environ['USER']}/.mozilla/managed-storage/slopspotter.json",
]


def install_manifests():
    print("Manifest:", MANIFEST)
    for manifest_fname in manifest_fnames:
        print(manifest_fname)
        os.makedirs(os.path.dirname(manifest_fname), exist_ok=True)
        with open(manifest_fname, "w") as file:
            json.dump(MANIFEST, file, indent=4)
    st = os.stat(MANIFEST["path"])
    os.chmod(MANIFEST["path"], st.st_mode | stat.S_IEXEC)


def main():
    parser = argparse.ArgumentParser(
        prog="slopspotter",
        description="CLI setup for slopspotter",
    )
    parser.add_argument("command")
    args = parser.parse_args()

    if args.command == "install_manifests":
        install_manifests()
    else:
        raise TypeError("invalid command")


if __name__ == "__main__":
    main()
