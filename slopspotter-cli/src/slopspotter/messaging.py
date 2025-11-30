"""Functions for sending & receiving native messages on STDIN & STDOUT, respectively."""

import json
import logging
import struct
import sys
from typing import Any, NamedTuple


class NativeMessage(NamedTuple):
    """An message to be sent via native messaging."""

    raw_length: bytes
    """The length of the native message, represented as bytes for transmission."""
    raw_content: bytes
    """The raw content of the native message, represented as bytes for transmission."""
    length: int
    """The length of the native message"""
    content: Any
    """The actual content of the native message."""

    @classmethod
    def from_content(cls, content: Any):
        """Create & encode a native message based on its unencoded message content.

        To get the most compact JSON representation, we specify (',', ':') to
        eliminate whitespace. We want the most compact representation because the
        browser rejects messages that exceed 1 MB.

        Args:
            content: JSON-serializable message content
        """
        raw_content = json.dumps(content, separators=(",", ":")).encode("utf-8")
        length = len(raw_content)
        raw_length = struct.pack("@I", length)
        return cls(raw_length, raw_content, length, content)

    @classmethod
    def from_stdin(cls):
        """Create & decode a native message based on incoming data from STDIN.

        On the application side, native messages are serialized using UTF-8 encoded
        JSON and are preceded with an unsigned 32-bit value containing the message
        length in native byte order.
        """
        # Get 32-bit unsigned integer containing message length
        raw_length = sys.stdin.buffer.read(4)
        length = struct.unpack("@I", raw_length)[0]
        logging.debug("Message length: %d", length)
        if length == 0:
            logging.warning("Received message has length 0")
        raw_content = sys.stdin.buffer.read(length)
        content = json.loads(raw_content)
        logging.debug("Received message: %s", content)
        return cls(raw_length, raw_content, length, content)

    def to_stdout(self):
        """Send the encoded message to STDOUT."""
        sys.stdout.buffer.write(self.raw_length)
        sys.stdout.buffer.write(self.raw_content)
        sys.stdout.buffer.flush()
