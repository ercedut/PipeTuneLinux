"""WAV analysis for explicit microphone verification."""

from __future__ import annotations

import json
import math
from pathlib import Path
import wave

from pipetune.verify.models import MicAnalysisResult

DEFAULT_VERIFICATION_DIR = Path("verification/microphone")
LATEST_VERIFICATION_PATH = DEFAULT_VERIFICATION_DIR / "latest-mic-verification.json"

_SILENCE_RMS_THRESHOLD = 0.005
_SILENCE_PEAK_THRESHOLD = 0.01
_CLIPPING_THRESHOLD = 0.98


def _full_scale(sample_width_bytes: int) -> int:
    if sample_width_bytes == 1:
        return 127
    if sample_width_bytes in {2, 3, 4}:
        return (1 << (8 * sample_width_bytes - 1)) - 1
    raise ValueError("unsupported sample width")


def _sample_value(chunk: bytes, sample_width_bytes: int) -> int:
    if sample_width_bytes == 1:
        # 8-bit PCM WAV commonly stores unsigned values.
        return chunk[0] - 128
    return int.from_bytes(chunk, byteorder="little", signed=True)


def _analyze_pcm(raw_frames: bytes, sample_width_bytes: int) -> tuple[int, float, float]:
    step = sample_width_bytes
    if step <= 0:
        return 0, 0.0, 0.0

    total_samples = len(raw_frames) // step
    if total_samples == 0:
        return 0, 0.0, 0.0

    max_abs = 0
    sum_sq = 0.0

    for offset in range(0, total_samples * step, step):
        sample = _sample_value(raw_frames[offset : offset + step], sample_width_bytes)
        abs_sample = abs(sample)
        if abs_sample > max_abs:
            max_abs = abs_sample
        sum_sq += float(sample * sample)

    rms = math.sqrt(sum_sq / total_samples)
    return total_samples, float(max_abs), float(rms)


def _status_for_metrics(peak_norm: float, rms_norm: float) -> tuple[bool, bool, str]:
    clipping_detected = peak_norm >= _CLIPPING_THRESHOLD
    silence_likely = rms_norm < _SILENCE_RMS_THRESHOLD or peak_norm < _SILENCE_PEAK_THRESHOLD

    if clipping_detected:
        status = "clipping_detected"
    elif silence_likely:
        status = "silence_likely"
    elif peak_norm > 0 or rms_norm > 0:
        status = "signal_detected"
    else:
        status = "unknown"

    return clipping_detected, silence_likely, status


def _invalid_result(path: Path, reason: str) -> MicAnalysisResult:
    return MicAnalysisResult(
        file_path=str(path),
        duration_seconds=0.0,
        sample_rate=0,
        channels=0,
        sample_width_bytes=0,
        frame_count=0,
        peak_amplitude=0.0,
        peak_normalized=0.0,
        rms_amplitude=0.0,
        rms_normalized=0.0,
        clipping_detected=False,
        silence_likely=False,
        status="invalid_file",
    )


def _analysis_json_path(wav_file: Path) -> Path:
    return wav_file.with_suffix(".analysis.json")


def _write_analysis_json(result: MicAnalysisResult, output_path: Path) -> None:
    payload = result.to_dict()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _update_latest(result: MicAnalysisResult, latest_path: Path | None = None) -> None:
    resolved_latest_path = latest_path or LATEST_VERIFICATION_PATH
    resolved_latest_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_latest_path.write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True), encoding="utf-8")


def _is_within_directory(path: Path, directory: Path) -> bool:
    try:
        resolved_path = path.resolve(strict=False)
        resolved_dir = directory.resolve(strict=False)
        resolved_path.relative_to(resolved_dir)
        return True
    except ValueError:
        return False


def _should_update_latest(wav_file: Path, update_status: bool | None) -> bool:
    if update_status is True:
        return True
    if update_status is False:
        return False
    # Default safety behavior: only project-local verification files update latest status.
    return _is_within_directory(wav_file, DEFAULT_VERIFICATION_DIR)


def analyze_wav_file(wav_file: Path, *, update_status: bool | None = None) -> MicAnalysisResult:
    if not wav_file.exists() or not wav_file.is_file():
        return _invalid_result(wav_file, "file missing")

    try:
        with wave.open(str(wav_file), "rb") as wav:
            channels = wav.getnchannels()
            sample_rate = wav.getframerate()
            sample_width = wav.getsampwidth()
            frame_count = wav.getnframes()
            comp_type = wav.getcomptype()

            if comp_type != "NONE":
                return _invalid_result(wav_file, "unsupported compression")
            if sample_width not in {1, 2, 3, 4}:
                return _invalid_result(wav_file, "unsupported sample width")

            raw_frames = wav.readframes(frame_count)
    except (wave.Error, OSError):
        return _invalid_result(wav_file, "invalid wave file")

    total_samples, peak_amplitude, rms_amplitude = _analyze_pcm(raw_frames, sample_width)
    full_scale = float(_full_scale(sample_width)) if sample_width else 1.0

    peak_norm = min(1.0, peak_amplitude / full_scale) if full_scale else 0.0
    rms_norm = min(1.0, rms_amplitude / full_scale) if full_scale else 0.0

    clipping_detected, silence_likely, status = _status_for_metrics(peak_norm, rms_norm)

    duration_seconds = float(frame_count) / float(sample_rate) if sample_rate > 0 else 0.0

    result = MicAnalysisResult(
        file_path=str(wav_file),
        duration_seconds=duration_seconds,
        sample_rate=sample_rate,
        channels=channels,
        sample_width_bytes=sample_width,
        frame_count=frame_count,
        peak_amplitude=float(peak_amplitude),
        peak_normalized=float(peak_norm),
        rms_amplitude=float(rms_amplitude),
        rms_normalized=float(rms_norm),
        clipping_detected=clipping_detected,
        silence_likely=silence_likely,
        status=status,
    )

    analysis_path = _analysis_json_path(wav_file)
    _write_analysis_json(result, analysis_path)
    if _should_update_latest(wav_file, update_status):
        _update_latest(result)
    return result


def render_analysis_summary(result: MicAnalysisResult) -> str:
    lines = [
        "PipeTune Microphone WAV Analysis",
        "",
        f"File: {result.file_path}",
        f"Duration: {result.duration_seconds:.2f} s",
        f"Sample rate: {result.sample_rate} Hz",
        f"Channels: {result.channels}",
        f"Peak normalized: {result.peak_normalized:.3f}",
        f"RMS normalized: {result.rms_normalized:.3f}",
        f"Clipping detected: {'yes' if result.clipping_detected else 'no'}",
        f"Silence likely: {'yes' if result.silence_likely else 'no'}",
        f"Status: {result.status}",
        "",
        "Interpretation:",
    ]

    if result.status == "invalid_file":
        lines.append("- The WAV file could not be analyzed. Provide a valid PCM WAV file.")
    elif result.status == "signal_detected":
        lines.append("- A signal was detected. This suggests the selected capture route is functional.")
        lines.append("- This is not calibration-grade measurement.")
    elif result.status == "silence_likely":
        lines.append("- Signal appears silent or near-silent. Capture route may be present but input signal is weak/unavailable.")
        lines.append("- This is not calibration-grade measurement.")
    elif result.status == "clipping_detected":
        lines.append("- Signal clipping was detected. Input gain or signal path may be too hot.")
        lines.append("- This is not calibration-grade measurement.")
    else:
        lines.append("- Microphone status remains unknown from this file.")

    lines.extend(["", "No system configuration was modified."])
    return "\n".join(lines)
