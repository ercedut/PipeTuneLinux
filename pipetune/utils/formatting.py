"""Formatting helpers for terminal output."""

from __future__ import annotations


def format_status(label: str, value: str) -> str:
    return f"- {label}: {value}"


def bool_to_text(value: bool) -> str:
    return "yes" if value else "no"
