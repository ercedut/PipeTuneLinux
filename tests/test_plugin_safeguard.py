from __future__ import annotations

import math
from pathlib import Path

from pipetune import cli
from pipetune.plugin.safeguard import PLUGIN_DIR, db_to_gain, process_reference, run_offline_validation


def _sine(frequency_hz: float, *, sample_rate: int = 48000, duration_seconds: float = 1.0, amplitude: float = 0.5) -> list[float]:
    return [
        amplitude * math.sin(2.0 * math.pi * frequency_hz * index / sample_rate)
        for index in range(int(sample_rate * duration_seconds))
    ]


def _rms(samples: list[float]) -> float:
    return math.sqrt(sum(sample * sample for sample in samples) / len(samples))


def test_lv2_plugin_source_files_exist() -> None:
    assert (PLUGIN_DIR / "manifest.ttl").exists()
    assert (PLUGIN_DIR / "pipetune-safeguard.ttl").exists()
    assert (PLUGIN_DIR / "pipetune_safeguard.c").exists()
    assert (PLUGIN_DIR / "Makefile").exists()


def test_lv2_control_ranges_are_documented() -> None:
    ttl = (PLUGIN_DIR / "pipetune-safeguard.ttl").read_text(encoding="utf-8")

    assert 'lv2:symbol "preamp_db"' in ttl
    assert "lv2:default -6.0" in ttl
    assert "lv2:minimum -24.0" in ttl
    assert "lv2:maximum 0.0" in ttl
    assert 'lv2:symbol "highpass_hz"' in ttl
    assert "lv2:default 120.0" in ttl
    assert "lv2:minimum 60.0" in ttl
    assert "lv2:maximum 250.0" in ttl
    assert 'lv2:symbol "limiter_ceiling_db"' in ttl
    assert "lv2:default -1.0" in ttl
    assert "lv2:minimum -12.0" in ttl
    assert "lv2:maximum -0.1" in ttl
    assert 'lv2:symbol "bypass"' in ttl


def test_makefile_build_is_local_and_install_refuses_global_install() -> None:
    makefile = (PLUGIN_DIR / "Makefile").read_text(encoding="utf-8")

    assert "pipetune_safeguard.so" in makefile
    assert "lv2-devel" in makefile
    assert "Global install is intentionally unsupported" in makefile


def test_plugin_build_command_is_documented() -> None:
    doc = Path("docs/lv2-safeguard-plugin.md").read_text(encoding="utf-8")

    assert "pipetune plugin build --local" in doc
    assert "pipetune plugin validate --offline" in doc
    assert "lv2-devel" in doc


def test_reference_limiter_respects_ceiling() -> None:
    signal = _sine(1000.0, amplitude=1.5)

    out_l, out_r = process_reference(signal, signal, preamp_db=0.0, highpass_hz=120.0, limiter_ceiling_db=-6.0)

    ceiling = db_to_gain(-6.0) + 1e-9
    assert max(abs(sample) for sample in out_l) <= ceiling
    assert max(abs(sample) for sample in out_r) <= ceiling


def test_reference_preamp_reduces_gain() -> None:
    signal = _sine(1000.0, amplitude=0.5)

    out_l, _out_r = process_reference(signal, signal, preamp_db=-6.0, highpass_hz=60.0, limiter_ceiling_db=-0.1)

    assert _rms(out_l[1000:]) < _rms(signal[1000:]) * 0.55


def test_reference_highpass_attenuates_low_frequency_signal() -> None:
    low = _sine(40.0, amplitude=0.5)
    mid = _sine(1000.0, amplitude=0.5)

    low_out, _ = process_reference(low, low, preamp_db=0.0, highpass_hz=120.0, limiter_ceiling_db=-0.1)
    mid_out, _ = process_reference(mid, mid, preamp_db=0.0, highpass_hz=120.0, limiter_ceiling_db=-0.1)

    assert _rms(low_out[5000:]) < _rms(mid_out[5000:]) * 0.45


def test_reference_bypass_preserves_input_within_tolerance() -> None:
    signal = _sine(1000.0, amplitude=0.5)

    out_l, out_r = process_reference(
        signal,
        signal,
        preamp_db=-24.0,
        highpass_hz=250.0,
        limiter_ceiling_db=-12.0,
        bypass=1.0,
    )

    assert max(abs(a - b) for a, b in zip(out_l, signal)) < 1e-12
    assert max(abs(a - b) for a, b in zip(out_r, signal)) < 1e-12


def test_offline_validation_passes_and_does_not_install() -> None:
    result = run_offline_validation()

    assert result.passed is True
    assert any("limiter ceiling" in check for check in result.checks)
    assert any("did not install" in check for check in result.checks)


def test_plugin_cli_info_and_validate(capsys) -> None:
    info_exit = cli.main(["plugin", "info"])
    info = capsys.readouterr().out

    assert info_exit == 0
    assert "PipeTune LV2 Plugin" in info
    assert "safeguard" in info.lower()
    assert "does not install" in info

    validate_exit = cli.main(["plugin", "validate", "--offline"])
    validation = capsys.readouterr().out

    assert validate_exit == 0
    assert "Final verdict: pass" in validation
    assert "No global LV2 installation was performed." in validation


def test_plugin_cli_requires_local_and_offline_flags(capsys) -> None:
    build_exit = cli.main(["plugin", "build"])
    build_output = capsys.readouterr().out
    validate_exit = cli.main(["plugin", "validate"])
    validate_output = capsys.readouterr().out

    assert build_exit == 1
    assert "--local is required" in build_output
    assert validate_exit == 1
    assert "--offline is required" in validate_output

