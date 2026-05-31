"""Sanitization helpers for public-facing audit documents."""

from __future__ import annotations

import getpass
import re
import socket
from pathlib import Path


_EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b")
_LONG_TMP_PATH_RE = re.compile(r"/tmp/[^\s]{24,}")


def sanitize_text(
    text: str,
    *,
    username: str | None = None,
    hostname: str | None = None,
    home: Path | None = None,
) -> str:
    redacted = text
    username_value = username or getpass.getuser()
    hostname_value = hostname or socket.gethostname()
    home_path = (home or Path.home()).as_posix().rstrip("/")

    # Normalize home-like paths first.
    if home_path:
        redacted = redacted.replace(home_path, "~")
    if username_value:
        redacted = re.sub(rf"/home/{re.escape(username_value)}\b", "~", redacted)
        redacted = re.sub(rf"\b{re.escape(username_value)}\b", "<user>", redacted)
    if hostname_value:
        redacted = re.sub(rf"\b{re.escape(hostname_value)}\b", "<hostname>", redacted)

    redacted = _EMAIL_RE.sub("<email>", redacted)
    redacted = _LONG_TMP_PATH_RE.sub("<path>", redacted)
    return redacted
