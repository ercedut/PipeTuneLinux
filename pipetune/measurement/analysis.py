"""Approximate FFT-based sweep response analysis."""

from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

from pipetune.measurement import MeasurementError
from pipetune.measurement.wav import read_wav_mono


@dataclass(slots=True)
class SweepAnalysisReport:
    sweep_file: str
    recorded_file: str
    sample_rate: int
    duration_seconds: float
    peak_dbfs: float
    rms_dbfs: float
    clipping_detected: bool
    frequency_bins: list[float]
    magnitude_db: list[float]
    analysis_warning: str
    measurement_quality: str


def analyze_sweep(
    sweep_path: Path,
    recorded_path: Path,
    output_path: Path,
    *,
    csv_output: Path | None = None,
) -> SweepAnalysisReport:
    sweep = read_wav_mono(sweep_path)
    recorded = read_wav_mono(recorded_path)

    if sweep.sample_rate != recorded.sample_rate:
        raise MeasurementError(
            f"Sample rate mismatch: sweep is {sweep.sample_rate} Hz, recorded file is {recorded.sample_rate} Hz."
        )
    if not sweep.samples or not recorded.samples:
        raise MeasurementError("Sweep and recorded WAV files must contain audio.")

    peak = max(abs(sample) for sample in recorded.samples)
    rms = math.sqrt(sum(sample * sample for sample in recorded.samples) / len(recorded.samples))
    clipping_detected = peak >= 0.999
    peak_dbfs = _dbfs(peak)
    rms_dbfs = _dbfs(rms)
    quality, warning = _quality_from_levels(peak_dbfs, rms_dbfs, clipping_detected)
    bins, magnitudes = _frequency_response(sweep.samples, recorded.samples, sweep.sample_rate)

    report = SweepAnalysisReport(
        sweep_file=str(sweep_path),
        recorded_file=str(recorded_path),
        sample_rate=sweep.sample_rate,
        duration_seconds=recorded.duration_seconds,
        peak_dbfs=round(peak_dbfs, 3),
        rms_dbfs=round(rms_dbfs, 3),
        clipping_detected=clipping_detected,
        frequency_bins=[round(value, 3) for value in bins],
        magnitude_db=[round(value, 3) for value in magnitudes],
        analysis_warning=warning,
        measurement_quality=quality,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(asdict(report), indent=2) + "\n", encoding="utf-8")
    if csv_output is not None:
        write_response_csv(csv_output, report.frequency_bins, report.magnitude_db)
    return report


def write_response_csv(path: Path, frequencies: list[float], magnitudes: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["freq_hz", "magnitude_db"])
        for frequency, magnitude in zip(frequencies, magnitudes):
            writer.writerow([f"{frequency:.3f}", f"{magnitude:.3f}"])


def _quality_from_levels(peak_dbfs: float, rms_dbfs: float, clipping_detected: bool) -> tuple[str, str]:
    if clipping_detected:
        return "fail", "Recorded sweep is clipped. Lower playback or capture gain and record again."
    if peak_dbfs < -80 or rms_dbfs < -75:
        return "fail", "Recorded sweep is too quiet for reliable analysis."
    if peak_dbfs < -50 or rms_dbfs < -55:
        return "warn", "Recorded sweep is quiet; response is approximate and may be noise-dominated."
    return "pass", "Approximate FFT response only; built-in laptop microphones are uncalibrated."


def _frequency_response(sweep_samples: list[float], recorded_samples: list[float], sample_rate: int) -> tuple[list[float], list[float]]:
    usable_count = min(len(sweep_samples), len(recorded_samples))
    fft_size = _analysis_fft_size(usable_count)
    if fft_size < 1024:
        raise MeasurementError("Recorded sweep is too short for frequency analysis.")

    start = max(0, (usable_count - fft_size) // 2)
    sweep_window = _windowed_segment(sweep_samples[start : start + fft_size])
    recorded_window = _windowed_segment(recorded_samples[start : start + fft_size])

    sweep_fft = _fft(sweep_window)
    recorded_fft = _fft(recorded_window)
    frequencies = _log_frequency_bins(20.0, min(20000.0, sample_rate / 2.0 - 1.0), 48)
    magnitudes: list[float] = []
    epsilon = 1e-12

    for frequency in frequencies:
        index = min(fft_size // 2, max(1, int(round(frequency * fft_size / sample_rate))))
        recorded_mag = abs(recorded_fft[index])
        sweep_mag = abs(sweep_fft[index])
        magnitudes.append(20.0 * math.log10((recorded_mag + epsilon) / (sweep_mag + epsilon)))

    return frequencies, magnitudes


def _analysis_fft_size(sample_count: int) -> int:
    if sample_count <= 0:
        return 0
    max_size = min(sample_count, 32768)
    return 1 << (max_size.bit_length() - 1)


def _windowed_segment(samples: list[float]) -> list[complex]:
    count = len(samples)
    if count == 1:
        return [complex(samples[0], 0.0)]
    return [
        complex(sample * (0.5 - 0.5 * math.cos(2.0 * math.pi * index / (count - 1))), 0.0)
        for index, sample in enumerate(samples)
    ]


def _fft(values: list[complex]) -> list[complex]:
    count = len(values)
    if count & (count - 1):
        raise MeasurementError("FFT size must be a power of two.")

    output = values[:]
    j = 0
    for i in range(1, count):
        bit = count >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            output[i], output[j] = output[j], output[i]

    length = 2
    while length <= count:
        angle = -2.0 * math.pi / length
        root = complex(math.cos(angle), math.sin(angle))
        for start in range(0, count, length):
            factor = 1.0 + 0.0j
            half = length // 2
            for offset in range(half):
                even = output[start + offset]
                odd = output[start + offset + half] * factor
                output[start + offset] = even + odd
                output[start + offset + half] = even - odd
                factor *= root
        length *= 2

    return output


def _log_frequency_bins(start_hz: float, end_hz: float, count: int) -> list[float]:
    ratio = end_hz / start_hz
    return [start_hz * (ratio ** (index / (count - 1))) for index in range(count)]


def _dbfs(value: float) -> float:
    if value <= 0:
        return -120.0
    return 20.0 * math.log10(value)

