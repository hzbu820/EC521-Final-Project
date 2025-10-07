#!/usr/bin/env -S python3 -u

import argparse
import json
import logging
import os
import struct
import sys

logger = logging.getLogger(__name__)

logging.basicConfig(
    filename=os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "log.log"
    ),
    level=logging.DEBUG,
    encoding="utf-8",
    format="%(asctime)s - %(levelname)s - %(message)s",
)

MANIFEST = {
    "name": "slopspotter",
    "description": "Get info about a package suggested by an AI language model",
    "path": __file__,
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


# Read a message from stdin and decode it.
def get_message():
    raw_length = sys.stdin.buffer.read(4)
    if len(raw_length) == 0:
        return ""
    message_length = struct.unpack("@I", raw_length)[0]
    message = sys.stdin.buffer.read(message_length).decode("utf-8")
    return json.loads(message)


# Encode a message for transmission,
# given its content.
def encode_message(message_content):
    # https://docs.python.org/3/library/json.html#basic-usage
    # To get the most compact JSON representation, you should specify
    # (',', ':') to eliminate whitespace.
    # We want the most compact representation because the browser rejects # messages that exceed 1 MB.
    logging.debug("encoding message")
    encoded_content = json.dumps(message_content, separators=(",", ":")).encode("utf-8")
    encoded_length = struct.pack("@I", len(encoded_content))
    return {"length": encoded_length, "content": encoded_content}


# Send an encoded message to stdout
def send_message(encoded_message):
    sys.stdout.buffer.write(encoded_message["length"])
    sys.stdout.buffer.write(encoded_message["content"])
    sys.stdout.buffer.flush()


def loop() -> int:
    while True:
        received_message = get_message()
        if received_message == "ping":
            logging.debug("received ping, sending pong")
            send_message(encode_message("pong"))
    return 0


def main() -> int:
    logging.debug("starting __main__.main()")
    parser = argparse.ArgumentParser(
        prog="slopspotter",
    )
    parser.add_argument("manifest_path", nargs="?", default="")
    parser.add_argument("browser_specific_settings", nargs="?", default="")
    parser.add_argument("-i", "--install-manifests", action="store_true")

    args = parser.parse_args(sys.argv[1:])

    if args.install_manifests:
        install_manifests()
        return 0

    if args.manifest_path == "" or args.browser_specific_settings == "":
        return 1

    logging.debug("starting loop")
    return loop()


if __name__ == "__main__":
    sys.exit(main())
