from __future__ import annotations

import math
from pathlib import Path

from pipetune import cli
from pipetune.plugin import safeguard
from pipetune.plugin.safeguard import (
    PLUGIN_DIR,
    db_to_gain,
    process_reference,
    render_metadata_validation,
    run_metadata_validation,
    run_offline_validation,
    run_rt_safety_validation,
)


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
    assert "pipetune_safeguard.o" in makefile
    assert "lv2-devel" in makefile
    assert "-Wall" in makefile
    assert "-Wextra" in makefile
    assert "-Werror" in makefile
    assert "-fPIC" in makefile
    assert "check:" in makefile
    assert "Global install is intentionally unsupported" in makefile


def test_gitignore_excludes_local_plugin_build_artifacts() -> None:
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert "plugins/lv2/**/*.so" in gitignore
    assert "plugins/lv2/**/*.o" in gitignore
    assert "plugins/lv2/**/*.d" in gitignore
    assert "plugins/lv2/**/*.tmp" in gitignore


def test_plugin_build_command_is_documented() -> None:
    doc = Path("docs/lv2-safeguard-plugin.md").read_text(encoding="utf-8")

    assert "pipetune plugin build --local" in doc
    assert "pipetune plugin clean --local" in doc
    assert "pipetune plugin validate --offline" in doc
    assert "pipetune plugin validate --metadata" in doc
    assert "pipetune plugin validate --rt-safety" in doc
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


def test_reference_control_boundaries_are_clamped() -> None:
    signal = _sine(1000.0, amplitude=0.5)

    below_preamp, _ = process_reference(signal, signal, preamp_db=-100.0)
    min_preamp, _ = process_reference(signal, signal, preamp_db=-24.0)
    above_preamp, _ = process_reference(signal, signal, preamp_db=12.0)
    max_preamp, _ = process_reference(signal, signal, preamp_db=0.0)

    assert below_preamp == min_preamp
    assert above_preamp == max_preamp

    below_hp, _ = process_reference(signal, signal, highpass_hz=1.0)
    min_hp, _ = process_reference(signal, signal, highpass_hz=60.0)
    above_hp, _ = process_reference(signal, signal, highpass_hz=1000.0)
    max_hp, _ = process_reference(signal, signal, highpass_hz=250.0)

    assert below_hp == min_hp
    assert above_hp == max_hp

    below_limiter, _ = process_reference(signal, signal, preamp_db=0.0, limiter_ceiling_db=-99.0)
    min_limiter, _ = process_reference(signal, signal, preamp_db=0.0, limiter_ceiling_db=-12.0)
    above_limiter, _ = process_reference(signal, signal, preamp_db=0.0, limiter_ceiling_db=3.0)
    max_limiter, _ = process_reference(signal, signal, preamp_db=0.0, limiter_ceiling_db=-0.1)

    assert below_limiter == min_limiter
    assert above_limiter == max_limiter


def test_reference_invalid_controls_do_not_crash_and_limiter_stays_safe() -> None:
    signal = _sine(1000.0, amplitude=2.0)

    out_l, out_r = process_reference(
        signal,
        signal,
        preamp_db=math.nan,
        highpass_hz=math.nan,
        limiter_ceiling_db=math.nan,
        bypass=-1.0,
    )

    ceiling = db_to_gain(-1.0) + 1e-9
    assert max(abs(sample) for sample in out_l + out_r) <= ceiling


def test_offline_validation_passes_and_does_not_install() -> None:
    result = run_offline_validation()

    assert result.passed is True
    assert any("limiter ceiling" in check for check in result.checks)
    assert any("did not install" in check for check in result.checks)


def test_metadata_validation_passes_or_warns_only_for_optional_lv2_validate(monkeypatch) -> None:
    monkeypatch.setattr(safeguard.shutil, "which", lambda command: None if command == "lv2_validate" else "/usr/bin/tool")

    report = run_metadata_validation()
    rendered = render_metadata_validation(report)

    assert report.passed is True
    assert "manifest.ttl exists" in rendered
    assert "plugin URI is consistent" in rendered
    assert "lv2_validate is not installed" in rendered


def test_metadata_validation_json_output(monkeypatch) -> None:
    monkeypatch.setattr(safeguard.shutil, "which", lambda command: None if command == "lv2_validate" else "/usr/bin/tool")

    rendered = render_metadata_validation(run_metadata_validation(), json_output=True)

    assert '"passed": true' in rendered
    assert '"safety": [' in rendered


def test_rt_safety_validation_passes_for_current_source() -> None:
    report = run_rt_safety_validation()

    assert report.passed is True
    assert any("run() contains no obvious" in check for check in report.checks)
    assert any("preamp_db" in check for check in report.checks)


def test_rt_safety_validation_ignores_comments_and_fails_for_run_calls(tmp_path: Path) -> None:
    source = tmp_path / "bad.c"
    source.write_text(
        """
        // malloc() in a comment must not count.
        static void run(LV2_Handle instance, uint32_t sample_count) {
            (void)instance;
            (void)sample_count;
            printf("bad");
            malloc(4);
        }
        static float clampf(float value, float minimum, float maximum, float fallback) { return value; }
        """,
        encoding="utf-8",
    )

    report = run_rt_safety_validation(source)

    assert report.passed is False
    assert any("printf" in error and "malloc" in error for error in report.errors)


def test_plugin_clean_command_removes_artifacts_only(tmp_path: Path, monkeypatch) -> None:
    plugin_dir = tmp_path / "pipetune-safeguard.lv2"
    plugin_dir.mkdir()
    for source_name in safeguard.SOURCE_FILES:
        (plugin_dir / source_name).write_text("source", encoding="utf-8")
    for artifact_name in ("pipetune_safeguard.so", "pipetune_safeguard.o", "scratch.d", "scratch.tmp"):
        (plugin_dir / artifact_name).write_text("artifact", encoding="utf-8")
    monkeypatch.setattr(safeguard, "PLUGIN_DIR", plugin_dir)

    exit_code = cli.main(["plugin", "clean", "--local"])

    assert exit_code == 0
    for artifact_name in ("pipetune_safeguard.so", "pipetune_safeguard.o", "scratch.d", "scratch.tmp"):
        assert not (plugin_dir / artifact_name).exists()
    for source_name in safeguard.SOURCE_FILES:
        assert (plugin_dir / source_name).exists()


def test_build_dependency_detection_reports_fedora_instructions(monkeypatch) -> None:
    monkeypatch.setattr(safeguard.shutil, "which", lambda _command: None)
    monkeypatch.setattr(safeguard, "_lv2_headers_available", lambda: False)

    exit_code, output = safeguard.build_plugin_local()

    assert exit_code == 1
    assert "Missing build dependency: gcc" in output
    assert "Missing build dependency: make" in output
    assert "lv2-devel" in output
    assert "sudo dnf install gcc make lv2-devel" in output
    assert "PipeTune did not run sudo or install packages." in output


def test_plugin_cli_info_validate_and_safety_disclaimers(capsys, monkeypatch) -> None:
    monkeypatch.setattr(safeguard.shutil, "which", lambda command: None if command == "lv2_validate" else "/usr/bin/tool")

    info_exit = cli.main(["plugin", "info"])
    info = capsys.readouterr().out

    assert info_exit == 0
    assert "PipeTune LV2 Plugin" in info
    assert "safeguard" in info.lower()
    assert "does not install" in info
    assert "No audio routing was changed." in info

    validate_exit = cli.main(["plugin", "validate", "--offline"])
    validation = capsys.readouterr().out

    assert validate_exit == 0
    assert "Final verdict: pass" in validation
    assert "No global LV2 installation was performed." in validation
    assert "No audio routing was changed." in validation

    metadata_exit = cli.main(["plugin", "validate", "--metadata"])
    metadata = capsys.readouterr().out

    assert metadata_exit == 0
    assert "Metadata Validation" in metadata
    assert "No PipeWire, WirePlumber, ALSA, service, system, or user audio configuration was modified." in metadata

    rt_exit = cli.main(["plugin", "validate", "--rt-safety"])
    rt_output = capsys.readouterr().out

    assert rt_exit == 0
    assert "RT-Safety Validation" in rt_output
    assert "No audio routing was changed." in rt_output


class _FakeProcess:
    def __init__(self, returncode: int, stdout: str) -> None:
        self.returncode = returncode
        self.stdout = stdout


def test_classify_lv2_validate_failure_sord_validate_not_found() -> None:
    result = safeguard._classify_lv2_validate_failure("/usr/bin/lv2_validate: 16: sord_validate: not found")
    assert result == "missing_helper"


def test_classify_lv2_validate_failure_no_such_file() -> None:
    result = safeguard._classify_lv2_validate_failure("sord_validate: No such file or directory")
    assert result == "missing_helper"


def test_classify_lv2_validate_failure_command_not_found() -> None:
    result = safeguard._classify_lv2_validate_failure("sord_validate: command not found")
    assert result == "missing_helper"


def test_classify_lv2_validate_failure_actual_ttl_error() -> None:
    result = safeguard._classify_lv2_validate_failure(
        "error: lv2:minimum must be a number\nerror: plugin validation failed"
    )
    assert result == "actual_failure"


def test_classify_lv2_validate_failure_empty_output() -> None:
    result = safeguard._classify_lv2_validate_failure("")
    assert result == "actual_failure"


def test_metadata_validation_warns_not_fails_for_missing_sord_validate(monkeypatch) -> None:
    monkeypatch.setattr(safeguard.shutil, "which", lambda command: "/usr/bin/lv2_validate")
    monkeypatch.setattr(
        safeguard.subprocess,
        "run",
        lambda *args, **kwargs: _FakeProcess(127, "/usr/bin/lv2_validate: 16: sord_validate: not found\n"),
    )

    report = run_metadata_validation()

    assert report.passed is True
    assert any("helper dependency is missing" in w for w in report.warnings)
    assert not report.errors


def test_metadata_validation_warns_not_fails_for_no_such_file_helper(monkeypatch) -> None:
    monkeypatch.setattr(safeguard.shutil, "which", lambda command: "/usr/bin/lv2_validate")
    monkeypatch.setattr(
        safeguard.subprocess,
        "run",
        lambda *args, **kwargs: _FakeProcess(127, "sord_validate: No such file or directory\n"),
    )

    report = run_metadata_validation()

    assert report.passed is True
    assert any("helper dependency is missing" in w for w in report.warnings)
    assert not report.errors


def test_metadata_validation_warns_not_fails_for_command_not_found_helper(monkeypatch) -> None:
    monkeypatch.setattr(safeguard.shutil, "which", lambda command: "/usr/bin/lv2_validate")
    monkeypatch.setattr(
        safeguard.subprocess,
        "run",
        lambda *args, **kwargs: _FakeProcess(127, "sord_validate: command not found\n"),
    )

    report = run_metadata_validation()

    assert report.passed is True
    assert any("helper dependency is missing" in w for w in report.warnings)
    assert not report.errors


def test_metadata_validation_fails_for_actual_ttl_error(monkeypatch) -> None:
    monkeypatch.setattr(safeguard.shutil, "which", lambda command: "/usr/bin/lv2_validate")
    monkeypatch.setattr(
        safeguard.subprocess,
        "run",
        lambda *args, **kwargs: _FakeProcess(1, "error: lv2:minimum must be a number\nerror: plugin validation failed\n"),
    )

    report = run_metadata_validation()

    assert report.passed is False
    assert any("lv2_validate failed" in e for e in report.errors)
    assert not report.warnings or not any("helper dependency" in w for w in report.warnings)


def test_metadata_validation_json_includes_warnings_for_missing_helper(monkeypatch) -> None:
    import json

    monkeypatch.setattr(safeguard.shutil, "which", lambda command: "/usr/bin/lv2_validate")
    monkeypatch.setattr(
        safeguard.subprocess,
        "run",
        lambda *args, **kwargs: _FakeProcess(127, "/usr/bin/lv2_validate: 16: sord_validate: not found\n"),
    )

    data = json.loads(render_metadata_validation(run_metadata_validation(), json_output=True))

    assert data["passed"] is True
    assert data["errors"] == []
    assert any("helper dependency is missing" in w for w in data["warnings"])


def test_plugin_cli_requires_local_and_offline_flags(capsys) -> None:
    build_exit = cli.main(["plugin", "build"])
    build_output = capsys.readouterr().out
    validate_exit = cli.main(["plugin", "validate"])
    validate_output = capsys.readouterr().out
    clean_exit = cli.main(["plugin", "clean"])
    clean_output = capsys.readouterr().out

    assert build_exit == 1
    assert "--local is required" in build_output
    assert validate_exit == 1
    assert "choose exactly one" in validate_output
    assert clean_exit == 1
    assert "--local is required" in clean_output
