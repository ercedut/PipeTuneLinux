from __future__ import annotations

from pathlib import Path

from pipetune.hardware.sanitize import sanitize_text


def test_sanitizer_redacts_username() -> None:
    text = "user erce logged in"
    redacted = sanitize_text(text, username="erce", hostname="host", home=Path("/home/erce"))
    assert "erce" not in redacted
    assert "<user>" in redacted


def test_sanitizer_redacts_hostname() -> None:
    text = "Host: my-laptop"
    redacted = sanitize_text(text, username="erce", hostname="my-laptop", home=Path("/home/erce"))
    assert "my-laptop" not in redacted
    assert "<hostname>" in redacted


def test_sanitizer_redacts_home_path() -> None:
    text = "/home/erce/Belgeler/GitHub"
    redacted = sanitize_text(text, username="erce", hostname="host", home=Path("/home/erce"))
    assert "/home/erce" not in redacted
    assert redacted.startswith("~/")


def test_sanitizer_leaves_normal_technical_terms_intact() -> None:
    text = "PipeWire default source alsa_input and HDA codec"
    redacted = sanitize_text(text, username="erce", hostname="host", home=Path("/home/erce"))
    assert "PipeWire" in redacted
    assert "alsa_input" in redacted
    assert "HDA codec" in redacted
