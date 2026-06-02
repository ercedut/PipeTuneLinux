from __future__ import annotations

from pathlib import Path
import struct
import wave

from pipetune.verify.mic_analyze import analyze_wav_file


def _write_wav(path: Path, samples: list[int], *, channels: int = 1, sample_rate: int = 44100) -> None:
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = b"".join(struct.pack("<h", sample) for sample in samples)
        wav.writeframes(frames)


def test_mic_analyze_detects_non_silent_signal(tmp_path: Path) -> None:
    wav_path = tmp_path / "signal.wav"
    samples = [1000, -1000, 2000, -2000] * 2000
    _write_wav(wav_path, samples)

    result = analyze_wav_file(wav_path)

    assert result.status == "signal_detected"
    assert result.silence_likely is False


def test_mic_analyze_detects_silent_signal(tmp_path: Path) -> None:
    wav_path = tmp_path / "silent.wav"
    samples = [0] * 4000
    _write_wav(wav_path, samples)

    result = analyze_wav_file(wav_path)

    assert result.status == "silence_likely"
    assert result.silence_likely is True


def test_mic_analyze_detects_clipping(tmp_path: Path) -> None:
    wav_path = tmp_path / "clipped.wav"
    samples = [32767, -32768] * 3000
    _write_wav(wav_path, samples)

    result = analyze_wav_file(wav_path)

    assert result.status == "clipping_detected"
    assert result.clipping_detected is True


def test_mic_analyze_handles_invalid_wav_file(tmp_path: Path) -> None:
    wav_path = tmp_path / "invalid.wav"
    wav_path.write_text("not a wav", encoding="utf-8")

    result = analyze_wav_file(wav_path)

    assert result.status == "invalid_file"


def test_mic_analyze_external_wav_does_not_update_latest_by_default(monkeypatch, tmp_path: Path) -> None:
    verification_dir = tmp_path / "verification" / "microphone"
    latest_path = verification_dir / "latest-mic-verification.json"
    monkeypatch.setattr("pipetune.verify.mic_analyze.DEFAULT_VERIFICATION_DIR", verification_dir)
    monkeypatch.setattr("pipetune.verify.mic_analyze.LATEST_VERIFICATION_PATH", latest_path)

    external_wav = tmp_path / "external" / "signal.wav"
    external_wav.parent.mkdir(parents=True, exist_ok=True)
    _write_wav(external_wav, [1200, -1200, 1000, -1000] * 2000)

    result = analyze_wav_file(external_wav)

    assert result.status in {"signal_detected", "clipping_detected", "silence_likely"}
    assert latest_path.exists() is False


def test_mic_analyze_project_local_wav_updates_latest(monkeypatch, tmp_path: Path) -> None:
    verification_dir = tmp_path / "verification" / "microphone"
    latest_path = verification_dir / "latest-mic-verification.json"
    monkeypatch.setattr("pipetune.verify.mic_analyze.DEFAULT_VERIFICATION_DIR", verification_dir)
    monkeypatch.setattr("pipetune.verify.mic_analyze.LATEST_VERIFICATION_PATH", latest_path)

    local_wav = verification_dir / "mic-test.wav"
    local_wav.parent.mkdir(parents=True, exist_ok=True)
    _write_wav(local_wav, [900, -900, 700, -700] * 2000)

    result = analyze_wav_file(local_wav)

    assert result.status in {"signal_detected", "clipping_detected", "silence_likely"}
    assert latest_path.exists() is True
