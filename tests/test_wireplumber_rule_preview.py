"""Tests for v0.8.1 WirePlumber rule preview, Bluetooth policy audit, and route recommendations."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

import pipetune
from pipetune import cli
from pipetune.packaging import REPO_ROOT
from pipetune.wireplumber import bluetooth as bt_mod
from pipetune.wireplumber import preview as prev_mod
from pipetune.wireplumber import recommend as rec_mod
from pipetune.wireplumber.bluetooth import BluetoothPolicyReport, run_bluetooth_policy_audit
from pipetune.wireplumber.preview import (
    PreviewValidationReport,
    RulePreviewReport,
    run_suggest_rule,
    run_validate_preview,
)
from pipetune.wireplumber.recommend import RouteRecommendReport, run_route_recommend


# ---------------------------------------------------------------------------
# Version check
# ---------------------------------------------------------------------------


def test_version_is_092() -> None:
    assert pipetune.__version__ == "0.9.2"


def test_codename_is_bluetooth_or_preview() -> None:
    assert any(kw in pipetune.CODENAME for kw in ("Bluetooth", "Preview", "LV2", "CI", "WirePlumber", "User", "Install", "Rule", "Integrity"))


# ---------------------------------------------------------------------------
# Bluetooth policy audit — unit tests
# ---------------------------------------------------------------------------


def test_bluetooth_policy_audit_no_devices():
    report = run_bluetooth_policy_audit(wpctl_status="", pactl_cards="")
    assert report.bluetooth_available is False or report.bluetooth_available is None or not report.hfp_hsp_suspected
    assert not report.errors


def test_bluetooth_policy_audit_hfp_warns():
    wpctl_status = "* 61. Sony WH-1000XM4 (HSP/HFP)  [vol: 0.80]\n"
    report = run_bluetooth_policy_audit(wpctl_status=wpctl_status, pactl_cards="")
    assert report.hfp_hsp_suspected
    assert any("HSP/HFP" in w or "hfp" in w.lower() for w in report.warnings)
    assert report.verdict == "warn"


def test_bluetooth_policy_audit_a2dp_ok():
    wpctl_status = "* 61. Sony WH-1000XM4 (A2DP Sink)  [vol: 0.80]\n"
    report = run_bluetooth_policy_audit(wpctl_status=wpctl_status, pactl_cards="")
    assert report.a2dp_ok
    assert not report.hfp_hsp_suspected
    assert any("A2DP" in c for c in report.checks)


def test_bluetooth_policy_audit_unknown_codec():
    wpctl_status = "* 61. SomeBTDevice [bluez]  [vol: 0.80]\n"
    report = run_bluetooth_policy_audit(wpctl_status=wpctl_status, pactl_cards="")
    assert isinstance(report.codec, str)


def test_bluetooth_policy_audit_no_bluetooth():
    report = run_bluetooth_policy_audit(wpctl_status="* 51. HD-Audio Generic  [vol: 0.65]\n", pactl_cards="")
    assert not report.hfp_hsp_suspected
    assert not report.a2dp_ok


def test_bluetooth_policy_audit_is_readonly():
    report = run_bluetooth_policy_audit(wpctl_status="", pactl_cards="")
    assert any("read-only" in c for c in report.checks)


def test_bluetooth_policy_audit_json_schema():
    report = run_bluetooth_policy_audit(wpctl_status="", pactl_cards="")
    output = bt_mod.render_bluetooth_policy_audit_json(report)
    data = json.loads(output)
    assert "command" in data
    assert "pipetune_version" in data
    assert "hfp_hsp_suspected" in data
    assert "a2dp_ok" in data
    assert "safety" in data
    assert data["safety"]["read_only"] is True
    assert data["safety"]["changed_bluetooth_profile"] is False


def test_bluetooth_policy_audit_malformed_input():
    report = run_bluetooth_policy_audit(wpctl_status="GARBAGE\nDATA\n!!!", pactl_cards="")
    assert not report.errors


# ---------------------------------------------------------------------------
# Bluetooth policy audit — CLI
# ---------------------------------------------------------------------------


def test_bluetooth_policy_audit_cli_exits_zero(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        "pipetune.cli.run_bluetooth_policy_audit",
        lambda **kw: BluetoothPolicyReport(
            passed=True,
            checks=["no Bluetooth audio devices detected", "bluetooth policy audit is read-only: no Bluetooth profile was changed"],
            warnings=[],
            errors=[],
        ),
    )
    exit_code = cli.main(["bluetooth", "policy-audit"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "PipeTune Bluetooth Policy Audit" in output
    assert "No Bluetooth profile was changed." in output


def test_bluetooth_policy_audit_cli_json(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        "pipetune.cli.run_bluetooth_policy_audit",
        lambda **kw: BluetoothPolicyReport(
            passed=True, checks=["ok"], warnings=[], errors=[], collected_at="2026-01-01T00:00:00+00:00"
        ),
    )
    exit_code = cli.main(["bluetooth", "policy-audit", "--json"])
    output = capsys.readouterr().out
    assert exit_code == 0
    data = json.loads(output)
    assert data["safety"]["changed_bluetooth_profile"] is False


def test_bluetooth_policy_audit_no_mutation(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        "pipetune.cli.run_bluetooth_policy_audit",
        lambda **kw: BluetoothPolicyReport(
            passed=True, checks=["ok"], warnings=[], errors=[], collected_at="2026-01-01T00:00:00+00:00"
        ),
    )
    cli.main(["bluetooth", "policy-audit"])
    output = capsys.readouterr().out
    assert "No Bluetooth profile was changed." in output
    assert "No audio routing was changed." in output


# ---------------------------------------------------------------------------
# WirePlumber suggest-rule — safety guards
# ---------------------------------------------------------------------------


def test_suggest_rule_requires_dry_run(tmp_path: Path) -> None:
    report = run_suggest_rule(dry_run=False, user_only=True, output_path=None, repo_root=tmp_path)
    assert report.verdict == "fail"
    assert any("--dry-run" in e for e in report.errors)


def test_suggest_rule_requires_user_only(tmp_path: Path) -> None:
    report = run_suggest_rule(dry_run=True, user_only=False, output_path=None, repo_root=tmp_path)
    assert report.verdict == "fail"
    assert any("--user-only" in e for e in report.errors)


def test_suggest_rule_requires_both_flags(tmp_path: Path) -> None:
    report = run_suggest_rule(dry_run=False, user_only=False, output_path=None, repo_root=tmp_path)
    assert report.verdict == "fail"


def test_suggest_rule_succeeds_with_both_flags(tmp_path: Path) -> None:
    report = run_suggest_rule(dry_run=True, user_only=True, output_path=None, repo_root=tmp_path)
    assert report.verdict in ("pass", "warn")
    assert not report.errors


def test_suggest_rule_writes_to_allowed_path(tmp_path: Path) -> None:
    output_path = tmp_path / "previews" / "wireplumber" / "test-rule.lua"
    report = run_suggest_rule(dry_run=True, user_only=True, output_path=output_path, repo_root=tmp_path)
    assert report.verdict in ("pass", "warn")
    assert not report.errors
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "PREVIEW ONLY" in content
    assert "NOT INSTALLED" in content


def test_suggest_rule_writes_to_reports_wireplumber_path(tmp_path: Path) -> None:
    output_path = tmp_path / "reports" / "wireplumber" / "test.lua"
    report = run_suggest_rule(dry_run=True, user_only=True, output_path=output_path, repo_root=tmp_path)
    assert not report.errors


def test_suggest_rule_refuses_config_path(tmp_path: Path) -> None:
    home = Path.home()
    output_path = home / ".config" / "wireplumber" / "test.lua"
    report = run_suggest_rule(dry_run=True, user_only=True, output_path=output_path, repo_root=tmp_path)
    assert report.verdict == "fail"
    assert any("~/.config" in e or ".config" in e for e in report.errors)


def test_suggest_rule_refuses_etc_path(tmp_path: Path) -> None:
    output_path = Path("/etc/wireplumber/test.lua")
    report = run_suggest_rule(dry_run=True, user_only=True, output_path=output_path, repo_root=tmp_path)
    assert report.verdict == "fail"
    assert any("/etc" in e for e in report.errors)


def test_suggest_rule_refuses_outside_repo_path(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-repo" / "test.lua"
    report = run_suggest_rule(dry_run=True, user_only=True, output_path=outside, repo_root=tmp_path)
    assert report.verdict == "fail"
    assert any("repo" in e.lower() or "refused" in e.lower() for e in report.errors)


def test_suggest_rule_refuses_non_allowed_subdir(tmp_path: Path) -> None:
    output_path = tmp_path / "src" / "test.lua"
    report = run_suggest_rule(dry_run=True, user_only=True, output_path=output_path, repo_root=tmp_path)
    assert report.verdict == "fail"


def test_suggest_rule_preview_contains_safety_warning(tmp_path: Path) -> None:
    output_path = tmp_path / "previews" / "wireplumber" / "test.lua"
    run_suggest_rule(dry_run=True, user_only=True, output_path=output_path, repo_root=tmp_path)
    content = output_path.read_text(encoding="utf-8")
    assert "PREVIEW ONLY" in content
    assert "NOT INSTALLED" in content


def test_suggest_rule_cli_refuses_without_dry_run(capsys) -> None:
    exit_code = cli.main(["wireplumber", "suggest-rule", "--user-only"])
    output = capsys.readouterr().out
    assert exit_code == 1
    assert "refused" in output or "fail" in output


def test_suggest_rule_cli_refuses_without_user_only(capsys) -> None:
    exit_code = cli.main(["wireplumber", "suggest-rule", "--dry-run"])
    output = capsys.readouterr().out
    assert exit_code == 1
    assert "refused" in output or "fail" in output


def test_suggest_rule_cli_no_mutation(capsys) -> None:
    cli.main(["wireplumber", "suggest-rule", "--dry-run", "--user-only"])
    output = capsys.readouterr().out
    assert "No WirePlumber rule was installed." in output


def test_suggest_rule_cli_json(capsys) -> None:
    exit_code = cli.main(["wireplumber", "suggest-rule", "--dry-run", "--user-only", "--json"])
    output = capsys.readouterr().out
    data = json.loads(output)
    assert "safety" in data
    assert data["safety"]["rule_installed"] is False
    assert data["safety"]["changed_routing"] is False


# ---------------------------------------------------------------------------
# WirePlumber validate-preview
# ---------------------------------------------------------------------------


def test_validate_preview_passes_valid_file(tmp_path: Path) -> None:
    preview_path = tmp_path / "previews" / "wireplumber" / "test.lua"
    preview_path.parent.mkdir(parents=True)
    preview_path.write_text(
        "-- PREVIEW ONLY — NOT INSTALLED\n-- This is a safe preview\n",
        encoding="utf-8",
    )
    report = run_validate_preview(path=preview_path, repo_root=tmp_path)
    assert report.passed
    assert report.verdict == "pass"


def test_validate_preview_fails_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "previews" / "wireplumber" / "missing.lua"
    report = run_validate_preview(path=missing, repo_root=tmp_path)
    assert report.verdict == "fail"
    assert any("does not exist" in e for e in report.errors)


def test_validate_preview_fails_missing_preview_only_marker(tmp_path: Path) -> None:
    preview_path = tmp_path / "previews" / "wireplumber" / "test.lua"
    preview_path.parent.mkdir(parents=True)
    preview_path.write_text("-- NOT INSTALLED\n-- some rule\n", encoding="utf-8")
    report = run_validate_preview(path=preview_path, repo_root=tmp_path)
    assert any("PREVIEW ONLY" in e for e in report.errors)


def test_validate_preview_fails_missing_not_installed_marker(tmp_path: Path) -> None:
    preview_path = tmp_path / "previews" / "wireplumber" / "test.lua"
    preview_path.parent.mkdir(parents=True)
    preview_path.write_text("-- PREVIEW ONLY\n-- some rule\n", encoding="utf-8")
    report = run_validate_preview(path=preview_path, repo_root=tmp_path)
    assert any("NOT INSTALLED" in e for e in report.errors)


def test_validate_preview_fails_config_path(tmp_path: Path) -> None:
    home = Path.home()
    config_path = home / ".config" / "wireplumber" / "test.lua"
    report = run_validate_preview(path=config_path, repo_root=tmp_path)
    assert report.verdict == "fail"


def test_validate_preview_fails_outside_repo(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.lua"
    outside.write_text("-- PREVIEW ONLY — NOT INSTALLED\n", encoding="utf-8")
    report = run_validate_preview(path=outside, repo_root=tmp_path)
    assert report.verdict == "fail"


def test_validate_preview_fails_on_dangerous_os_execute(tmp_path: Path) -> None:
    preview_path = tmp_path / "previews" / "wireplumber" / "test.lua"
    preview_path.parent.mkdir(parents=True)
    preview_path.write_text(
        "-- PREVIEW ONLY — NOT INSTALLED\nos.execute('rm -rf /')\n",
        encoding="utf-8",
    )
    report = run_validate_preview(path=preview_path, repo_root=tmp_path)
    assert any("dangerous" in e for e in report.errors)


def test_validate_preview_cli_passes(capsys, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "pipetune.cli.run_validate_preview",
        lambda path, **kw: PreviewValidationReport(
            passed=True, checks=["ok"], warnings=[], errors=[], path=str(path)
        ),
    )
    exit_code = cli.main(["wireplumber", "validate-preview", str(tmp_path / "test.lua")])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "PipeTune WirePlumber Validate Preview" in output


def test_validate_preview_cli_json(capsys, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "pipetune.cli.run_validate_preview",
        lambda path, **kw: PreviewValidationReport(
            passed=True, checks=["ok"], warnings=[], errors=[], path=str(path)
        ),
    )
    exit_code = cli.main(["wireplumber", "validate-preview", str(tmp_path / "test.lua"), "--json"])
    output = capsys.readouterr().out
    data = json.loads(output)
    assert data["safety"]["read_only"] is True


# ---------------------------------------------------------------------------
# Route recommend
# ---------------------------------------------------------------------------


def test_route_recommend_no_sinks_warns():
    report = run_route_recommend(pactl_info="", pactl_sinks="", wpctl_status="")
    assert any("sinks" in w or "routing" in w.lower() for w in report.warnings)
    assert any("sinks" in r or "PipeWire" in r or "routing" in r.lower() for r in report.recommendations)


def test_route_recommend_basic_pass():
    pactl_info = (
        "Server String: /run/user/1000/pulse/native\n"
        "Default Sink: alsa_output.pci-0000_00_1f.3.analog-stereo\n"
        "Default Source: alsa_input.pci-0000_00_1f.3.analog-stereo\n"
    )
    pactl_sinks = "Sink #51\n\tName: alsa_output.pci-0000_00_1f.3.analog-stereo\n\tDescription: Test\n"
    report = run_route_recommend(pactl_info=pactl_info, pactl_sinks=pactl_sinks, wpctl_status="")
    assert any("default sink" in c for c in report.checks)
    assert report.verdict in ("pass", "warn")


def test_route_recommend_bluetooth_hfp_recommends():
    wpctl_status = "* 61. Sony WH-1000XM4 (HSP/HFP)  [vol: 0.80]\n"
    pactl_sinks = "Sink #61\n\tName: bluez_output.AB_CD\n\tDescription: Sony\n"
    report = run_route_recommend(pactl_info="", pactl_sinks=pactl_sinks, wpctl_status=wpctl_status)
    assert any("HFP" in r or "A2DP" in r for r in report.recommendations)


def test_route_recommend_a2dp_no_recommendation():
    wpctl_status = "* 61. My Headphones (A2DP Sink)  [vol: 0.80]\n"
    pactl_sinks = "Sink #61\n\tName: bluez_output.AB_CD\n"
    report = run_route_recommend(pactl_info="", pactl_sinks=pactl_sinks, wpctl_status=wpctl_status)
    assert not any("A2DP" in r for r in report.recommendations)


def test_route_recommend_is_readonly():
    report = run_route_recommend(pactl_info="", pactl_sinks="", wpctl_status="")
    assert any("read-only" in c for c in report.checks)


def test_route_recommend_json_schema():
    report = run_route_recommend(pactl_info="", pactl_sinks="", wpctl_status="")
    output = rec_mod.render_route_recommend_json(report)
    data = json.loads(output)
    assert "command" in data
    assert "recommendations" in data
    assert "safety" in data
    assert data["safety"]["read_only"] is True
    assert data["safety"]["changed_routing"] is False


def test_route_recommend_cli_exits_zero(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        "pipetune.cli.run_route_recommend",
        lambda **kw: RouteRecommendReport(
            checks=["no route mismatch detected", "route recommend is read-only: no routing changed, no config modified"],
            warnings=[],
            recommendations=[],
            collected_at="2026-01-01T00:00:00+00:00",
        ),
    )
    exit_code = cli.main(["route", "recommend"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "PipeTune Route Recommendations" in output
    assert "No routing was changed." in output


def test_route_recommend_cli_json(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        "pipetune.cli.run_route_recommend",
        lambda **kw: RouteRecommendReport(
            checks=["ok"], warnings=[], recommendations=[], collected_at="2026-01-01T00:00:00+00:00"
        ),
    )
    exit_code = cli.main(["route", "recommend", "--json"])
    output = capsys.readouterr().out
    assert exit_code == 0
    data = json.loads(output)
    assert data["safety"]["read_only"] is True
    assert "recommendations" in data


def test_route_recommend_no_mutation(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        "pipetune.cli.run_route_recommend",
        lambda **kw: RouteRecommendReport(
            checks=["ok"], warnings=[], recommendations=[], collected_at="2026-01-01T00:00:00+00:00"
        ),
    )
    cli.main(["route", "recommend"])
    output = capsys.readouterr().out
    assert "No routing was changed." in output
    assert "No audio routing was changed." in output


# ---------------------------------------------------------------------------
# No mutation safety flags across all new commands
# ---------------------------------------------------------------------------


def test_all_new_commands_have_safety_flags():
    """JSON safety blocks confirm read-only behavior for all new 0.8.1 commands."""
    report_bt = run_bluetooth_policy_audit(wpctl_status="", pactl_cards="")
    bt_data = json.loads(bt_mod.render_bluetooth_policy_audit_json(report_bt))
    assert bt_data["safety"]["read_only"] is True
    assert bt_data["safety"]["changed_bluetooth_profile"] is False

    report_suggest = run_suggest_rule(dry_run=True, user_only=True, output_path=None)
    suggest_data = json.loads(prev_mod.render_suggest_rule_json(report_suggest))
    assert suggest_data["safety"]["rule_installed"] is False
    assert suggest_data["safety"]["changed_routing"] is False

    report_rec = run_route_recommend(pactl_info="", pactl_sinks="", wpctl_status="")
    rec_data = json.loads(rec_mod.render_route_recommend_json(report_rec))
    assert rec_data["safety"]["changed_routing"] is False


# ---------------------------------------------------------------------------
# Documentation checks
# ---------------------------------------------------------------------------


def test_docs_wireplumber_rule_preview_exists() -> None:
    doc = REPO_ROOT / "docs" / "wireplumber-rule-preview.md"
    assert doc.exists(), "docs/wireplumber-rule-preview.md is missing"


def test_docs_bluetooth_policy_diagnostics_exists() -> None:
    doc = REPO_ROOT / "docs" / "bluetooth-policy-diagnostics.md"
    assert doc.exists(), "docs/bluetooth-policy-diagnostics.md is missing"


def test_previews_wireplumber_dir_exists() -> None:
    assert (REPO_ROOT / "previews" / "wireplumber").is_dir()
