"""Minimal WAV I/O and diagnostics helpers for measurement commands."""

from __future__ import annotations

import json
import math
import struct
import wave
from array import array
from dataclasses import asdict, dataclass
from pathlib import Path

from pipetune.measurement import MeasurementError

CLIPPING_THRESHOLD = 0.999
SILENCE_PEAK_THRESHOLD = 1e-5
SILENCE_RMS_THRESHOLD = 1e-5
DC_OFFSET_WARN_THRESHOLD = 0.02
MIN_ANALYSIS_SECONDS = 0.05


@dataclass(slots=True)
class WavData:
    sample_rate: int
    samples: list[float]
    channels: int
    sample_width_or_format: str = "unknown"

    @property
    def duration_seconds(self) -> float:
        if self.sample_rate <= 0:
            return 0.0
        return len(self.samples) / self.sample_rate


@dataclass(slots=True)
class WavDiagnostics:
    path: str
    channel_count: int
    sample_width_or_format: str
    sample_rate: int
    duration_seconds: float
    peak_dbfs: float
    rms_dbfs: float
    peak_linear: float
    rms_linear: float
    dc_offset: float
    clipping_detected: bool
    silence_detected: bool
    dominant_frequency_hz: float | None
    quality_flags: list[str]
    measurement_quality: str
    warnings: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def write_mono_pcm16(path: Path, samples: list[float], sample_rate: int) -> None:
    if sample_rate <= 0:
        raise MeasurementError("Sample rate must be positive.")
    if not samples:
        raise MeasurementError("Cannot write an empty WAV file.")

    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = array("h")
    for sample in samples:
        value = max(-1.0, min(1.0, sample))
        pcm.append(int(round(value * 32767)))

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm.tobytes())


def write_pcm16(path: Path, channels: list[list[float]], sample_rate: int) -> None:
    if sample_rate <= 0:
        raise MeasurementError("Sample rate must be positive.")
    if not channels or not channels[0]:
        raise MeasurementError("Cannot write an empty WAV file.")

    frame_count = len(channels[0])
    channel_count = len(channels)
    if any(len(channel) != frame_count for channel in channels):
        raise MeasurementError("All WAV channels must have the same sample count.")

    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = array("h")
    for frame_index in range(frame_count):
        for channel in channels:
            value = max(-1.0, min(1.0, channel[frame_index]))
            pcm.append(int(round(value * 32767)))

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(channel_count)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm.tobytes())


def write_mono_float32(path: Path, samples: list[float], sample_rate: int) -> None:
    if sample_rate <= 0:
        raise MeasurementError("Sample rate must be positive.")
    if not samples:
        raise MeasurementError("Cannot write an empty WAV file.")

    data = b"".join(struct.pack("<f", max(-1.0, min(1.0, sample))) for sample in samples)
    fmt = struct.pack("<HHIIHH", 3, 1, sample_rate, sample_rate * 4, 4, 32)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as output:
        output.write(b"RIFF")
        output.write(struct.pack("<I", 4 + (8 + len(fmt)) + (8 + len(data))))
        output.write(b"WAVE")
        output.write(b"fmt ")
        output.write(struct.pack("<I", len(fmt)))
        output.write(fmt)
        output.write(b"data")
        output.write(struct.pack("<I", len(data)))
        output.write(data)


def read_wav_mono(path: Path) -> WavData:
    return read_wav(path)


def read_wav(path: Path) -> WavData:
    if not path.exists():
        raise MeasurementError(f"WAV file does not exist: {path}")

    try:
        with wave.open(str(path), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            frame_count = wav_file.getnframes()
            raw = wav_file.readframes(frame_count)
    except EOFError as exc:
        raise MeasurementError(f"Invalid WAV file: {path}") from exc
    except wave.Error as exc:
        return _read_riff_wave(path, exc)

    if channels <= 0 or sample_rate <= 0:
        raise MeasurementError(f"Invalid WAV metadata: {path}")
    if frame_count <= 0 or not raw:
        raise MeasurementError(f"WAV file contains no audio: {path}")

    sample_format = _pcm_format_label(sample_width)
    samples = _decode_pcm(raw, sample_width, channels)
    if not samples:
        raise MeasurementError(f"WAV file contains no decodable audio: {path}")

    return WavData(
        sample_rate=sample_rate,
        samples=samples,
        channels=channels,
        sample_width_or_format=sample_format,
    )


def inspect_wav(path: Path) -> WavDiagnostics:
    data = read_wav(path)
    if not data.samples:
        raise MeasurementError(f"WAV file contains no audio: {path}")

    peak = max(abs(sample) for sample in data.samples)
    rms = math.sqrt(sum(sample * sample for sample in data.samples) / len(data.samples))
    dc_offset = sum(data.samples) / len(data.samples)
    clipping_detected = peak >= CLIPPING_THRESHOLD
    silence_detected = peak <= SILENCE_PEAK_THRESHOLD or rms <= SILENCE_RMS_THRESHOLD
    duration = data.duration_seconds
    dominant_frequency = dominant_frequency_hz(data.samples, data.sample_rate)

    flags: list[str] = []
    warnings: list[str] = []
    if clipping_detected:
        flags.append("clipping")
        warnings.append("Fail: measured samples are near full scale and likely clipped.")
    if silence_detected:
        flags.append("silence")
        warnings.append("Fail: measured signal is silent or too quiet for useful analysis.")
    if abs(dc_offset) >= DC_OFFSET_WARN_THRESHOLD:
        flags.append("dc_offset")
        warnings.append("Warning: measured signal has notable DC offset.")
    if duration < MIN_ANALYSIS_SECONDS:
        flags.append("very_short")
        warnings.append("Fail: WAV duration is too short for trustworthy measurement analysis.")
    elif duration < 0.25:
        flags.append("short")
        warnings.append("Warning: WAV duration is short; measurement is approximate.")

    if clipping_detected or silence_detected or duration < MIN_ANALYSIS_SECONDS:
        quality = "fail"
    elif flags:
        quality = "warn"
    else:
        quality = "pass"
        warnings.append("Pass: measured WAV levels are usable for approximate analysis.")

    warnings.append("Built-in laptop microphones remain approximate and uncalibrated.")

    return WavDiagnostics(
        path=str(path),
        channel_count=data.channels,
        sample_width_or_format=data.sample_width_or_format,
        sample_rate=data.sample_rate,
        duration_seconds=round(duration, 6),
        peak_dbfs=round(_dbfs(peak), 3),
        rms_dbfs=round(_dbfs(rms), 3),
        peak_linear=round(peak, 8),
        rms_linear=round(rms, 8),
        dc_offset=round(dc_offset, 8),
        clipping_detected=clipping_detected,
        silence_detected=silence_detected,
        dominant_frequency_hz=round(dominant_frequency, 3) if dominant_frequency is not None else None,
        quality_flags=flags,
        measurement_quality=quality,
        warnings=warnings,
    )


def render_wav_diagnostics(diagnostics: WavDiagnostics, *, json_output: bool = False) -> str:
    if json_output:
        return json.dumps(diagnostics.to_dict(), indent=2)

    lines = [
        "PipeTune WAV Inspection",
        f"- Path: {diagnostics.path}",
        f"- Sample rate: {diagnostics.sample_rate} Hz",
        f"- Duration: {diagnostics.duration_seconds:g} seconds",
        f"- Channels: {diagnostics.channel_count}",
        f"- Sample format: {diagnostics.sample_width_or_format}",
        f"- Peak: {diagnostics.peak_dbfs:g} dBFS ({diagnostics.peak_linear:g} linear)",
        f"- RMS: {diagnostics.rms_dbfs:g} dBFS ({diagnostics.rms_linear:g} linear)",
        f"- DC offset: {diagnostics.dc_offset:g}",
        f"- Clipping detected: {'yes' if diagnostics.clipping_detected else 'no'}",
        f"- Silence detected: {'yes' if diagnostics.silence_detected else 'no'}",
        f"- Dominant frequency estimate: {_frequency_label(diagnostics.dominant_frequency_hz)}",
        f"- Verdict: {diagnostics.measurement_quality}",
        "",
        "Warnings:",
    ]
    lines.extend(f"- {warning}" for warning in diagnostics.warnings)
    lines.append("")
    lines.append("No system configuration was modified.")
    return "\n".join(lines)


def dominant_frequency_hz(samples: list[float], sample_rate: int) -> float | None:
    if sample_rate <= 0 or len(samples) < 16:
        return None
    size = 1 << (min(len(samples), 8192).bit_length() - 1)
    if size < 16:
        return None
    start = max(0, (len(samples) - size) // 2)
    segment = samples[start : start + size]
    mean = sum(segment) / len(segment)
    windowed = [
        complex((sample - mean) * (0.5 - 0.5 * math.cos(2.0 * math.pi * index / (size - 1))), 0.0)
        for index, sample in enumerate(segment)
    ]
    spectrum = _fft(windowed)
    magnitudes = [abs(value) for value in spectrum[: size // 2]]
    if len(magnitudes) <= 1:
        return None
    dominant_index = max(range(1, len(magnitudes)), key=magnitudes.__getitem__)
    if magnitudes[dominant_index] <= 1e-12:
        return None
    return dominant_index * sample_rate / size


def _decode_pcm(raw: bytes, sample_width: int, channels: int) -> list[float]:
    if sample_width == 1:
        values = [(byte - 128) / 128.0 for byte in raw]
    elif sample_width == 2:
        pcm = array("h")
        pcm.frombytes(raw)
        values = [sample / 32768.0 for sample in pcm]
    elif sample_width == 3:
        values = []
        for index in range(0, len(raw), 3):
            chunk = raw[index : index + 3]
            if len(chunk) < 3:
                break
            integer = int.from_bytes(chunk + (b"\xff" if chunk[2] & 0x80 else b"\x00"), "little", signed=True)
            values.append(integer / 8388608.0)
    elif sample_width == 4:
        pcm32 = array("i")
        pcm32.frombytes(raw)
        values = [sample / 2147483648.0 for sample in pcm32]
    else:
        raise MeasurementError(f"Unsupported WAV sample width: {sample_width} bytes")

    if channels == 1:
        return [float(value) for value in values if math.isfinite(value)]

    mono: list[float] = []
    for index in range(0, len(values), channels):
        frame = values[index : index + channels]
        if len(frame) == channels:
            mono.append(sum(frame) / channels)
    return mono


def _read_riff_wave(path: Path, original_error: wave.Error) -> WavData:
    raw = path.read_bytes()
    try:
        if len(raw) < 12 or raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
            raise MeasurementError(f"Invalid WAV file: {path}") from original_error

        offset = 12
        format_tag: int | None = None
        channels: int | None = None
        sample_rate: int | None = None
        bits_per_sample: int | None = None
        data_chunk = b""
        while offset + 8 <= len(raw):
            chunk_id = raw[offset : offset + 4]
            chunk_size = struct.unpack("<I", raw[offset + 4 : offset + 8])[0]
            chunk_start = offset + 8
            chunk_end = chunk_start + chunk_size
            chunk_data = raw[chunk_start:chunk_end]
            if chunk_id == b"fmt ":
                if len(chunk_data) < 16:
                    raise MeasurementError(f"Invalid WAV fmt chunk: {path}")
                format_tag, channels, sample_rate, _byte_rate, _block_align, bits_per_sample = struct.unpack(
                    "<HHIIHH",
                    chunk_data[:16],
                )
            elif chunk_id == b"data":
                data_chunk = chunk_data
            offset = chunk_end + (chunk_size % 2)

        if format_tag is None or channels is None or sample_rate is None or bits_per_sample is None:
            raise MeasurementError(f"Invalid WAV metadata: {path}")
        if not data_chunk:
            raise MeasurementError(f"WAV file contains no audio: {path}")
        if format_tag != 3 or bits_per_sample != 32:
            raise MeasurementError(f"Unsupported WAV format tag: {format_tag}") from original_error
        values = [item[0] for item in struct.iter_unpack("<f", data_chunk)]
        samples = _mix_channels([float(value) for value in values if math.isfinite(value)], channels)
        if not samples:
            raise MeasurementError(f"WAV file contains no decodable audio: {path}")
        return WavData(
            sample_rate=sample_rate,
            samples=samples,
            channels=channels,
            sample_width_or_format="float32",
        )
    except struct.error as exc:
        raise MeasurementError(f"Invalid WAV file: {path}") from exc


def _mix_channels(values: list[float], channels: int) -> list[float]:
    if channels <= 1:
        return values
    mono: list[float] = []
    for index in range(0, len(values), channels):
        frame = values[index : index + channels]
        if len(frame) == channels:
            mono.append(sum(frame) / channels)
    return mono


def _pcm_format_label(sample_width: int) -> str:
    labels = {
        1: "pcm_u8",
        2: "pcm_s16",
        3: "pcm_s24",
        4: "pcm_s32",
    }
    return labels.get(sample_width, f"pcm_{sample_width * 8}")


def _dbfs(value: float) -> float:
    if value <= 0:
        return -120.0
    return 20.0 * math.log10(value)


def _frequency_label(frequency: float | None) -> str:
    if frequency is None:
        return "not available"
    return f"{frequency:g} Hz"


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
