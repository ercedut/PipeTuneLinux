"""Tests for v0.9.2 WirePlumber install-preflight and install-guide commands."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import pipetune
from pipetune import cli
from pipetune.wireplumber.preflight import (
    PreflightReport,
    render_preflight_report,
    render_preflight_report_json,
    run_install_preflight,
)
from pipetune.wireplumber.guide import (
    render_install_guide,
    render_install_guide_json,
)


def _isolated_dirs(tmp_path: Path) -> tuple[Path, Path]:
    rule_dir = tmp_path / "config" / "wireplumber" / "wireplumber.conf.d"
    manifest_path = tmp_path / "state" / "wireplumber-rules" / "manifests.json"
    return rule_dir, manifest_path


# ---------------------------------------------------------------------------
# Version check
# ---------------------------------------------------------------------------

def test_version_is_100rc1() -> None:
    assert pipetune.__version__ == "1.0.0rc1"


# ---------------------------------------------------------------------------
# install-preflight: basic behavior
# ---------------------------------------------------------------------------

def test_preflight_is_read_only_no_files_created(tmp_path: Path) -> None:
    rule_dir, manifest_path = _isolated_dirs(tmp_path)
    files_before = set(tmp_path.rglob("*"))

    run_install_preflight(rule_dir=rule_dir, manifest_path=manifest_path)

    files_after = set(tmp_path.rglob("*"))
    assert files_after == files_before, "preflight must not create any files"


def test_preflight_missing_config_dir_is_warning_not_error(tmp_path: Path) -> None:
    rule_dir, manifest_path = _isolated_dirs(tmp_path)

    report = run_install_preflight(rule_dir=rule_dir, manifest_path=manifest_path)

    assert not report.config_dir_exists
    assert any("does not exist" in w for w in report.warnings)
    assert not any("does not exist" in e for e in report.errors)


def test_preflight_existing_config_dir_reports_writable(tmp_path: Path) -> None:
    rule_dir, manifest_path = _isolated_dirs(tmp_path)
    rule_dir.mkdir(parents=True)

    report = run_install_preflight(rule_dir=rule_dir, manifest_path=manifest_path)

    assert report.config_dir_exists
    assert report.config_dir_writable


def test_preflight_verdict_pass_or_warn_in_clean_isolated_env(tmp_path: Path) -> None:
    rule_dir, manifest_path = _isolated_dirs(tmp_path)

    report = run_install_preflight(rule_dir=rule_dir, manifest_path=manifest_path)

    assert report.verdict in ("pass", "warn")
    assert report.passed


def test_preflight_reports_manifest_path(tmp_path: Path) -> None:
    rule_dir, manifest_path = _isolated_dirs(tmp_path)

    report = run_install_preflight(rule_dir=rule_dir, manifest_path=manifest_path)

    assert str(manifest_path) in report.manifest_path


def test_preflight_reports_config_dir(tmp_path: Path) -> None:
    rule_dir, manifest_path = _isolated_dirs(tmp_path)

    report = run_install_preflight(rule_dir=rule_dir, manifest_path=manifest_path)

    assert str(rule_dir) in report.config_dir


def test_preflight_reports_env_var_isolation_state(tmp_path: Path, monkeypatch) -> None:
    rule_dir, manifest_path = _isolated_dirs(tmp_path)

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("PIPETUNE_HOME", str(tmp_path / "state"))

    report = run_install_preflight(rule_dir=rule_dir, manifest_path=manifest_path)

    assert report.xdg_config_home_set is True
    assert report.pipetune_home_set is True


def test_preflight_without_env_vars_reports_false(tmp_path: Path, monkeypatch) -> None:
    rule_dir, manifest_path = _isolated_dirs(tmp_path)

    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("PIPETUNE_HOME", raising=False)

    report = run_install_preflight(rule_dir=rule_dir, manifest_path=manifest_path)

    assert report.xdg_config_home_set is False
    assert report.pipetune_home_set is False


def test_preflight_reports_service_status_field(tmp_path: Path) -> None:
    rule_dir, manifest_path = _isolated_dirs(tmp_path)

    report = run_install_preflight(rule_dir=rule_dir, manifest_path=manifest_path)

    assert report.wireplumber_service_status in ("active", "inactive", "unknown", "failed", "activating")
    assert report.pipewire_service_status in ("active", "inactive", "unknown", "failed", "activating")


def test_preflight_checks_list_not_empty(tmp_path: Path) -> None:
    rule_dir, manifest_path = _isolated_dirs(tmp_path)

    report = run_install_preflight(rule_dir=rule_dir, manifest_path=manifest_path)

    assert len(report.checks) > 0


# ---------------------------------------------------------------------------
# install-preflight: render
# ---------------------------------------------------------------------------

def test_preflight_render_contains_verdict(tmp_path: Path) -> None:
    rule_dir, manifest_path = _isolated_dirs(tmp_path)
    report = run_install_preflight(rule_dir=rule_dir, manifest_path=manifest_path)

    text = render_preflight_report(report)

    assert "Final verdict:" in text
    assert "read-only" in text.lower() or "This command is read-only" in text


def test_preflight_render_contains_safety_lines(tmp_path: Path) -> None:
    rule_dir, manifest_path = _isolated_dirs(tmp_path)
    report = run_install_preflight(rule_dir=rule_dir, manifest_path=manifest_path)

    text = render_preflight_report(report)

    assert "No file was created" in text
    assert "No service was restarted" in text
    assert "No audio routing was changed" in text


# ---------------------------------------------------------------------------
# install-preflight: JSON output
# ---------------------------------------------------------------------------

def test_preflight_json_parses(tmp_path: Path) -> None:
    rule_dir, manifest_path = _isolated_dirs(tmp_path)
    report = run_install_preflight(rule_dir=rule_dir, manifest_path=manifest_path)

    data = json.loads(render_preflight_report_json(report))

    assert data["safety"]["read_only"] is True
    assert data["safety"]["wrote_files"] is False
    assert data["safety"]["restarted_services"] is False
    assert data["safety"]["changed_routing"] is False
    assert data["safety"]["modified_system"] is False
    assert "verdict" in data
    assert "checks" in data
    assert "warnings" in data
    assert "errors" in data


def test_preflight_json_contains_paths(tmp_path: Path) -> None:
    rule_dir, manifest_path = _isolated_dirs(tmp_path)
    report = run_install_preflight(rule_dir=rule_dir, manifest_path=manifest_path)

    data = json.loads(render_preflight_report_json(report))

    assert str(rule_dir) in data["config_dir"]
    assert str(manifest_path) in data["manifest_path"]


# ---------------------------------------------------------------------------
# install-preflight: CLI integration
# ---------------------------------------------------------------------------

def test_cli_install_preflight_exits_zero(tmp_path: Path, monkeypatch, capsys) -> None:
    from pipetune.wireplumber import preflight as pf_mod

    rule_dir, manifest_path = _isolated_dirs(tmp_path)
    monkeypatch.setattr(pf_mod, "get_wireplumber_rule_dir", lambda: rule_dir)
    monkeypatch.setattr(pf_mod, "get_manifest_path", lambda: manifest_path)

    exit_code = cli.main(["wireplumber", "install-preflight"])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "WirePlumber Install Preflight" in out


def test_cli_install_preflight_json(tmp_path: Path, monkeypatch, capsys) -> None:
    from pipetune.wireplumber import preflight as pf_mod

    rule_dir, manifest_path = _isolated_dirs(tmp_path)
    monkeypatch.setattr(pf_mod, "get_wireplumber_rule_dir", lambda: rule_dir)
    monkeypatch.setattr(pf_mod, "get_manifest_path", lambda: manifest_path)

    exit_code = cli.main(["wireplumber", "install-preflight", "--json"])
    out = capsys.readouterr().out

    assert exit_code == 0
    data = json.loads(out)
    assert data["safety"]["read_only"] is True


# ---------------------------------------------------------------------------
# install-guide: content
# ---------------------------------------------------------------------------

def test_install_guide_contains_dry_run_step() -> None:
    text = render_install_guide()

    assert "--dry-run" in text


def test_install_guide_contains_rollback_instruction() -> None:
    text = render_install_guide()

    assert "rollback-rule" in text


def test_install_guide_says_no_service_restart() -> None:
    text = render_install_guide()

    assert "does NOT restart" in text or "No service was restarted" in text


def test_install_guide_says_no_routing() -> None:
    text = render_install_guide()

    assert "does NOT route" in text or "No audio routing" in text


def test_install_guide_mentions_user_level_only() -> None:
    text = render_install_guide()

    assert "user-level" in text or "user only" in text.lower()


def test_install_guide_mentions_preflight() -> None:
    text = render_install_guide()

    assert "install-preflight" in text


# ---------------------------------------------------------------------------
# install-guide: JSON output
# ---------------------------------------------------------------------------

def test_install_guide_json_parses() -> None:
    data = json.loads(render_install_guide_json())

    assert data["safety"]["read_only"] is True
    assert data["safety"]["wrote_files"] is False
    assert data["safety"]["restarted_services"] is False
    assert "steps" in data
    assert "safety_notes" in data
    assert len(data["steps"]) > 0


def test_install_guide_json_dry_run_step_present() -> None:
    data = json.loads(render_install_guide_json())

    combined = " ".join(data["steps"])
    assert "--dry-run" in combined


def test_install_guide_json_rollback_step_present() -> None:
    data = json.loads(render_install_guide_json())

    combined = " ".join(data["steps"])
    assert "rollback-rule" in combined


# ---------------------------------------------------------------------------
# install-guide: CLI integration
# ---------------------------------------------------------------------------

def test_cli_install_guide_exits_zero(capsys) -> None:
    exit_code = cli.main(["wireplumber", "install-guide"])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "WirePlumber Install Guide" in out


def test_cli_install_guide_json(capsys) -> None:
    exit_code = cli.main(["wireplumber", "install-guide", "--json"])
    out = capsys.readouterr().out

    assert exit_code == 0
    data = json.loads(out)
    assert data["safety"]["read_only"] is True


# ---------------------------------------------------------------------------
# install-rule: improved dry-run output (v0.9.2)
# ---------------------------------------------------------------------------

_VALID_PREVIEW_CONTENT = """\
-- PREVIEW ONLY — NOT INSTALLED
-- Generated by PipeTune Linux
-- This file is a skeleton for manual review only.
rule = {
  matches = {},
  apply_properties = {},
}
"""


def _make_preview(tmp_path: Path, name: str = "test-rule.lua") -> Path:
    p = tmp_path / "previews" / "wireplumber" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(_VALID_PREVIEW_CONTENT, encoding="utf-8")
    return p


def test_install_rule_dry_run_output_says_no_file_written(tmp_path: Path, monkeypatch, capsys) -> None:
    from pipetune.wireplumber import install as inst_mod
    from pipetune.wireplumber.install import render_install_report, run_install_rule

    preview = _make_preview(tmp_path)
    rule_dir, manifest_path = _isolated_dirs(tmp_path)

    report = run_install_rule(
        str(preview), user_only=True, dry_run=True, confirm_install=False,
        rule_dir=rule_dir, manifest_path=manifest_path,
    )
    text = render_install_report(report)

    assert "No file was written" in text


def test_install_rule_dry_run_output_contains_confirm_command(tmp_path: Path) -> None:
    from pipetune.wireplumber.install import render_install_report, run_install_rule

    preview = _make_preview(tmp_path)
    rule_dir, manifest_path = _isolated_dirs(tmp_path)

    report = run_install_rule(
        str(preview), user_only=True, dry_run=True, confirm_install=False,
        rule_dir=rule_dir, manifest_path=manifest_path,
    )
    text = render_install_report(report)

    assert "--confirm-install" in text


def test_install_rule_confirmed_output_contains_rollback_command(tmp_path: Path) -> None:
    from pipetune.wireplumber.install import render_install_report, run_install_rule

    preview = _make_preview(tmp_path)
    rule_dir, manifest_path = _isolated_dirs(tmp_path)

    report = run_install_rule(
        str(preview), user_only=True, dry_run=False, confirm_install=True,
        rule_dir=rule_dir, manifest_path=manifest_path,
    )
    text = render_install_report(report)

    assert "rollback-rule" in text
    assert "--confirm-rollback" in text


def test_install_rule_confirmed_output_contains_manual_reload_warning(tmp_path: Path) -> None:
    from pipetune.wireplumber.install import render_install_report, run_install_rule

    preview = _make_preview(tmp_path)
    rule_dir, manifest_path = _isolated_dirs(tmp_path)

    report = run_install_rule(
        str(preview), user_only=True, dry_run=False, confirm_install=True,
        rule_dir=rule_dir, manifest_path=manifest_path,
    )
    text = render_install_report(report)

    assert "manually reload" in text.lower() or "manually restart" in text.lower()


# ---------------------------------------------------------------------------
# rollback-rule: improved safety output (v0.9.2)
# ---------------------------------------------------------------------------

def test_rollback_rule_dry_run_says_no_files_removed(tmp_path: Path) -> None:
    from pipetune.wireplumber.install import run_install_rule
    from pipetune.wireplumber.rollback import render_rollback_report, run_rollback_rule

    preview = _make_preview(tmp_path)
    rule_dir, manifest_path = _isolated_dirs(tmp_path)

    install_report = run_install_rule(
        str(preview), user_only=True, dry_run=False, confirm_install=True,
        rule_dir=rule_dir, manifest_path=manifest_path,
    )
    report = run_rollback_rule(
        install_report.install_id, dry_run=True, confirm_rollback=False,
        manifest_path=manifest_path,
    )
    text = render_rollback_report(report)

    assert "no files were removed" in text.lower() or "no files were modified" in text.lower()


def test_rollback_rule_confirmed_output_contains_manual_reload_warning(tmp_path: Path) -> None:
    from pipetune.wireplumber.install import run_install_rule
    from pipetune.wireplumber.rollback import render_rollback_report, run_rollback_rule

    preview = _make_preview(tmp_path)
    rule_dir, manifest_path = _isolated_dirs(tmp_path)

    install_report = run_install_rule(
        str(preview), user_only=True, dry_run=False, confirm_install=True,
        rule_dir=rule_dir, manifest_path=manifest_path,
    )
    report = run_rollback_rule(
        install_report.install_id, dry_run=False, confirm_rollback=True,
        manifest_path=manifest_path,
    )
    text = render_rollback_report(report)

    assert "manually reload" in text.lower() or "manually restart" in text.lower()


def test_rollback_rule_json_has_safety_block(tmp_path: Path) -> None:
    from pipetune.wireplumber.install import run_install_rule
    from pipetune.wireplumber.rollback import render_rollback_report_json, run_rollback_rule

    preview = _make_preview(tmp_path)
    rule_dir, manifest_path = _isolated_dirs(tmp_path)

    install_report = run_install_rule(
        str(preview), user_only=True, dry_run=False, confirm_install=True,
        rule_dir=rule_dir, manifest_path=manifest_path,
    )
    report = run_rollback_rule(
        install_report.install_id, dry_run=True, confirm_rollback=False,
        manifest_path=manifest_path,
    )
    data = json.loads(render_rollback_report_json(report))

    assert data["safety"]["restarted_services"] is False
    assert data["safety"]["changed_routing"] is False


# ---------------------------------------------------------------------------
# Preview artifact hygiene
# ---------------------------------------------------------------------------

def test_preview_wireplumber_gitkeep_tracked() -> None:
    gitkeep = Path(__file__).resolve().parents[1] / "previews" / "wireplumber" / ".gitkeep"
    assert gitkeep.exists(), "previews/wireplumber/.gitkeep must exist"


def test_gitignore_ignores_preview_lua_files() -> None:
    import subprocess
    repo_root = Path(__file__).resolve().parents[1]
    fake_lua = repo_root / "previews" / "wireplumber" / "test-rule.lua"
    try:
        fake_lua.write_text("-- test\n", encoding="utf-8")
        result = subprocess.run(
            ["git", "check-ignore", "-v", str(fake_lua)],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"previews/wireplumber/*.lua should be gitignored but git check-ignore returned {result.returncode}. "
            f"stdout: {result.stdout!r} stderr: {result.stderr!r}"
        )
    finally:
        if fake_lua.exists():
            fake_lua.unlink()


# ---------------------------------------------------------------------------
# No systemctl/routing calls in new modules
# ---------------------------------------------------------------------------

def test_no_systemctl_or_routing_in_preflight_or_guide() -> None:
    import inspect
    from pipetune.wireplumber import preflight, guide

    for module in (preflight, guide):
        src = inspect.getsource(module)
        assert "systemctl restart" not in src, f"systemctl restart found in {module.__name__}"
        assert "wpctl set-default" not in src
        assert "pactl set-default-sink" not in src
        assert "pactl set-card-profile" not in src
