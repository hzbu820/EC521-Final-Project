"""Tools for checking spelling and word validity."""

import os
import sys

UNIX_WORD_LIST_PATHS = [
    os.path.join("/", "usr", "dict", "words"),
    os.path.join("/", "usr", "share", "dict", "words"),
]


def unix_words_path():
    """Find the UNIX word list path of the current system."""
    if sys.platform == "win32":
        raise OSError("Windows does not have a word list")

    for word_list_path in UNIX_WORD_LIST_PATHS:
        if os.path.exists(word_list_path):
            return word_list_path
    return ""


WORD_SET = {}

if sys.platform != "win32":
    with open(unix_words_path()) as f:
        WORD_SET = set(line.strip().lower() for line in f)


def in_unix_words(package_name: str):
    """Check if the package's name is in Linux's default `words` lists.

    UNIX OSes usually come with a list of English words located in
    `/usr/share/dict/words` or `/usr/dict/words`. This is often used by other
    spell checking programs on the computer.

    Args:
        package_name: string of a package name

    Returns:
        in_words: True if the package's name is in `/usr/
    """
    if sys.platform == "win32":
        raise OSError("Windows does not have a word list")
    return package_name in WORD_SET
