"""Tests: rc command-matrix."""

import json

from pipetune.rc.command_matrix import (
    KNOWN_CATEGORIES,
    CommandEntry,
    render_command_matrix,
    render_command_matrix_json,
    run_command_matrix,
)


def test_command_matrix_runs():
    report = run_command_matrix()
    assert report.entries
    assert isinstance(report.entries[0], CommandEntry)


def test_command_matrix_passed():
    report = run_command_matrix()
    assert report.passed
    assert not report.errors


def test_command_matrix_all_categories_known():
    report = run_command_matrix()
    for entry in report.entries:
        assert entry.category in KNOWN_CATEGORIES, f"{entry.command} has unknown category: {entry.category}"


def test_command_matrix_no_blank_categories():
    report = run_command_matrix()
    for entry in report.entries:
        assert entry.category, f"{entry.command} has blank category"


def test_command_matrix_includes_major_groups():
    report = run_command_matrix()
    categories = {e.category for e in report.entries}
    required = {"hardware", "measure", "plugin", "package", "release", "profiles", "wireplumber", "route", "bluetooth", "rc"}
    for cat in required:
        assert cat in categories, f"category '{cat}' not found in command matrix"


def test_command_matrix_install_rule_writes_user_config():
    report = run_command_matrix()
    entry = next((e for e in report.entries if e.command == "wireplumber install-rule"), None)
    assert entry is not None, "wireplumber install-rule not in command matrix"
    assert entry.writes_user_config is True
    assert entry.requires_confirmation is True
    assert entry.has_dry_run is True


def test_command_matrix_rollback_rule_writes_user_config():
    report = run_command_matrix()
    entry = next((e for e in report.entries if e.command == "wireplumber rollback-rule"), None)
    assert entry is not None, "wireplumber rollback-rule not in command matrix"
    assert entry.writes_user_config is True
    assert entry.requires_confirmation is True
    assert entry.has_dry_run is True


def test_command_matrix_rc_audit_read_only():
    report = run_command_matrix()
    entry = next((e for e in report.entries if e.command == "rc audit"), None)
    assert entry is not None
    assert entry.read_only is True
    assert entry.writes_user_config is False


def test_command_matrix_release_check_read_only():
    report = run_command_matrix()
    entry = next((e for e in report.entries if e.command == "release check"), None)
    assert entry is not None
    assert entry.read_only is True


def test_command_matrix_json_parses():
    report = run_command_matrix()
    raw = render_command_matrix_json(report)
    parsed = json.loads(raw)
    assert "command_matrix" in parsed
    assert isinstance(parsed["command_matrix"], list)
    assert parsed["command_matrix"]
    assert "total" in parsed
    assert "safety" in parsed
    assert parsed["safety"]["read_only"] is True
    assert parsed["safety"]["modified_system"] is False


def test_command_matrix_json_safety_block():
    report = run_command_matrix()
    parsed = json.loads(render_command_matrix_json(report))
    safety = parsed["safety"]
    assert safety["read_only"] is True
    assert safety["modified_system"] is False
    assert safety["changed_routing"] is False
    assert safety["restarted_services"] is False
    assert safety["wrote_user_audio_config"] is False


def test_command_matrix_text_render():
    report = run_command_matrix()
    text = render_command_matrix(report)
    assert "RC Command Matrix" in text
    assert "wireplumber install-rule" in text
    assert "No audio routing was changed." in text


def test_command_matrix_entries_have_safety_notes():
    report = run_command_matrix()
    for entry in report.entries:
        assert entry.safety_notes, f"{entry.command} has no safety_notes"
