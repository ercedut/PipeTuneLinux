"""Models for guided repair planning outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class RepairContext:
    audit_dir: Path
    raw_dir: Path
    speaker_output_working: bool | None
    hda_retask_detected: bool | None
    mic_route_visible: bool | None
