from __future__ import annotations

from pipetune.repair.mic_test_plan import render_mic_test_plan


def test_mic_test_plan_warns_route_visible_not_proof() -> None:
    output = render_mic_test_plan()

    assert "Route visible does not mean microphone works." in output
    assert "Capture test must be explicit and user-approved." in output


def test_mic_test_plan_marks_recording_command_manual() -> None:
    output = render_mic_test_plan()

    assert "MANUAL / CREATES LOCAL AUDIO FILE / RUN ONLY IF YOU APPROVE RECORDING" in output
    assert "arecord -d 5 -f cd test-mic.wav" in output
