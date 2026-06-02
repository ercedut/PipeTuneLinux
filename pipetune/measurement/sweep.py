"""Logarithmic sine sweep generation."""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path

from pipetune import __version__
from pipetune.measurement import MeasurementError
from pipetune.measurement.wav import write_mono_pcm16

SAFE_PLAYBACK_WARNING = (
    "Generated sweep files can be loud. Keep playback volume low, increase slowly, "
    "and stop immediately if the speaker or listener is stressed."
)


def generate_log_sweep(
    output_path: Path,
    *,
    duration_seconds: float = 10.0,
    sample_rate: int = 48000,
    start_hz: float = 20.0,
    end_hz: float = 20000.0,
    amplitude: float = 0.5,
) -> Path:
    _validate_sweep_request(duration_seconds, sample_rate, start_hz, end_hz, amplitude)

    sample_count = int(round(duration_seconds * sample_rate))
    ratio_log = math.log(end_hz / start_hz)
    samples: list[float] = []
    fade_samples = max(1, min(int(sample_rate * 0.02), sample_count // 20))

    for index in range(sample_count):
        time_seconds = index / sample_rate
        phase = 2.0 * math.pi * start_hz * duration_seconds / ratio_log
        phase *= math.exp(ratio_log * time_seconds / duration_seconds) - 1.0
        envelope = 1.0
        if index < fade_samples:
            envelope = index / fade_samples
        elif index >= sample_count - fade_samples:
            envelope = (sample_count - index - 1) / fade_samples
        samples.append(amplitude * max(0.0, envelope) * math.sin(phase))

    write_mono_pcm16(output_path, samples, sample_rate)
    _write_metadata(output_path, duration_seconds, sample_rate, start_hz, end_hz, amplitude)
    return output_path


def _validate_sweep_request(
    duration_seconds: float,
    sample_rate: int,
    start_hz: float,
    end_hz: float,
    amplitude: float,
) -> None:
    if sample_rate <= 0:
        raise MeasurementError("Sample rate must be positive.")
    if duration_seconds <= 0:
        raise MeasurementError("Duration must be positive.")
    if amplitude <= 0:
        raise MeasurementError("Amplitude must be positive.")
    if amplitude > 0.9:
        raise MeasurementError("Unsafe amplitude: values above 0.9 are refused.")
    if start_hz <= 0 or end_hz <= 0:
        raise MeasurementError("Sweep frequencies must be positive.")
    if start_hz >= end_hz:
        raise MeasurementError("Invalid frequency range: start-hz must be lower than end-hz.")
    nyquist = sample_rate / 2.0
    if end_hz >= nyquist:
        raise MeasurementError(
            f"Invalid frequency range: end-hz must be below Nyquist ({nyquist:g} Hz)."
        )


def metadata_path_for_wav(wav_path: Path) -> Path:
    return wav_path.with_suffix(wav_path.suffix + ".json")


def _write_metadata(
    output_path: Path,
    duration_seconds: float,
    sample_rate: int,
    start_hz: float,
    end_hz: float,
    amplitude: float,
) -> None:
    metadata = {
        "sample_rate": sample_rate,
        "duration_seconds": duration_seconds,
        "start_hz": start_hz,
        "end_hz": end_hz,
        "amplitude": amplitude,
        "generated_at": datetime.now(UTC).isoformat(),
        "pipetune_version": __version__,
        "warning": SAFE_PLAYBACK_WARNING,
    }
    metadata_path_for_wav(output_path).write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
