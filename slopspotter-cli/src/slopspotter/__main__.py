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
def getMessage():
    rawLength = sys.stdin.buffer.read(4)
    if len(rawLength) == 0:
        return ""
    messageLength = struct.unpack("@I", rawLength)[0]
    message = sys.stdin.buffer.read(messageLength).decode("utf-8")
    return json.loads(message)


# Encode a message for transmission,
# given its content.
def encodeMessage(messageContent):
    # https://docs.python.org/3/library/json.html#basic-usage
    # To get the most compact JSON representation, you should specify
    # (',', ':') to eliminate whitespace.
    # We want the most compact representation because the browser rejects # messages that exceed 1 MB.
    logging.debug("encoding message")
    encodedContent = json.dumps(messageContent, separators=(",", ":")).encode("utf-8")
    encodedLength = struct.pack("@I", len(encodedContent))
    return {"length": encodedLength, "content": encodedContent}


# Send an encoded message to stdout
def sendMessage(encodedMessage):
    sys.stdout.buffer.write(encodedMessage["length"])
    sys.stdout.buffer.write(encodedMessage["content"])
    sys.stdout.buffer.flush()


def loop() -> int:
    while True:
        receivedMessage = getMessage()
        if receivedMessage == "ping":
            logging.debug("received ping, sending pong")
            sendMessage(encodeMessage("pong"))
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
