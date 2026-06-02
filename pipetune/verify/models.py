"""Models for explicit microphone verification."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class MicAnalysisResult:
    file_path: str
    duration_seconds: float
    sample_rate: int
    channels: int
    sample_width_bytes: int
    frame_count: int
    peak_amplitude: float
    peak_normalized: float
    rms_amplitude: float
    rms_normalized: float
    clipping_detected: bool
    silence_likely: bool
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MicCaptureResult:
    success: bool
    exit_code: int
    message: str
    output_file: Path | None
    analysis_result: MicAnalysisResult | None = None
