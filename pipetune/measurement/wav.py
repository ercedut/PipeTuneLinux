"""Minimal WAV I/O helpers for measurement commands."""

from __future__ import annotations

import math
import wave
from array import array
from dataclasses import dataclass
from pathlib import Path

from pipetune.measurement import MeasurementError


@dataclass(slots=True)
class WavData:
    sample_rate: int
    samples: list[float]
    channels: int

    @property
    def duration_seconds(self) -> float:
        if self.sample_rate <= 0:
            return 0.0
        return len(self.samples) / self.sample_rate


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


def read_wav_mono(path: Path) -> WavData:
    if not path.exists():
        raise MeasurementError(f"WAV file does not exist: {path}")

    try:
        with wave.open(str(path), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            frame_count = wav_file.getnframes()
            raw = wav_file.readframes(frame_count)
    except wave.Error as exc:
        raise MeasurementError(f"Invalid WAV file: {path}") from exc

    if channels <= 0 or sample_rate <= 0:
        raise MeasurementError(f"Invalid WAV metadata: {path}")
    if frame_count <= 0 or not raw:
        raise MeasurementError(f"WAV file contains no audio: {path}")

    samples = _decode_pcm(raw, sample_width, channels)
    if not samples:
        raise MeasurementError(f"WAV file contains no decodable audio: {path}")

    return WavData(sample_rate=sample_rate, samples=samples, channels=channels)


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

