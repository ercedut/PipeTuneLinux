from __future__ import annotations

import json
from pathlib import Path

from pipetune.verify.mic_status import render_mic_status


def test_mic_status_reports_not_tested_when_no_latest_json_exists(tmp_path: Path) -> None:
    latest = tmp_path / "latest-mic-verification.json"
    output = render_mic_status(latest)

    assert "State: not_tested" in output
    assert "capture has not been verified" in output


def test_mic_status_reads_latest_verification(tmp_path: Path) -> None:
    latest = tmp_path / "latest-mic-verification.json"
    latest.write_text(
        json.dumps(
            {
                "file_path": "verification/microphone/mic-test.wav",
                "status": "signal_detected",
                "duration_seconds": 5.0,
                "rms_normalized": 0.02,
                "peak_normalized": 0.2,
                "clipping_detected": False,
                "silence_likely": False,
            }
        ),
        encoding="utf-8",
    )

    output = render_mic_status(latest)

    assert "Status: signal_detected" in output
    assert "Duration: 5.00 s" in output
    assert "Clipping detected: no" in output


def test_mic_status_ignores_latest_json_pointing_outside_local_verification_dir(tmp_path: Path) -> None:
    latest = tmp_path / "latest-mic-verification.json"
    latest.write_text(
        json.dumps(
            {
                "file_path": "/tmp/pytest-of-user/pytest-999/test_fixture/clipped.wav",
                "status": "clipping_detected",
                "duration_seconds": 1.0,
                "rms_normalized": 0.0,
                "peak_normalized": 1.0,
                "clipping_detected": True,
                "silence_likely": False,
            }
        ),
        encoding="utf-8",
    )

    output = render_mic_status(latest)

    assert "State: invalid_status" in output
    assert "outside the local verification directory" in output
    assert "capture has not been verified" in output
