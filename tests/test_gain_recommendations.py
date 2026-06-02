from __future__ import annotations

from pipetune.gain.gain_recommendations import recommendation_for_status, render_gain_matrix, render_gain_plan


def test_clipping_recommendation_mentions_lowering_alsa_gain_stages() -> None:
    output = "\n".join(recommendation_for_status("clipping_detected"))

    assert "Lower ALSA Capture, Mic Boost, or Digital gain" in output


def test_silence_recommendation_mentions_gain_stage_threshold() -> None:
    output = "\n".join(recommendation_for_status("silence_likely"))

    assert "gain-stage threshold" in output


def test_signal_recommendation_says_document_current_gain_state() -> None:
    output = "\n".join(recommendation_for_status("signal_detected"))

    assert "Document current gain state" in output


def test_gain_matrix_includes_target_and_safety_footer() -> None:
    output = render_gain_matrix()

    assert "Peak normalized: 0.200-0.800" in output
    assert "pipetune verify mic-capture --duration 5 --confirm-recording --analyze" in output
    assert "No system configuration was modified." in output


def test_gain_plan_prints_manual_commands_only() -> None:
    output = render_gain_plan()

    assert "MANUAL / DO NOT RUN BLINDLY:" in output
    assert "amixer -c 0 set 'Capture' 60% cap" in output
    assert "No system configuration was modified." in output
