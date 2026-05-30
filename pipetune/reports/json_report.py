"""JSON report utilities."""

from __future__ import annotations

import json
from pathlib import Path


def build_json_report(diagnostic: dict) -> str:
    return json.dumps(diagnostic, indent=2, sort_keys=True)


def write_json_report(diagnostic: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_json_report(diagnostic), encoding="utf-8")
