"""Tests: rc audit."""

import json

from pipetune.rc.audit import (
    RcAuditReport,
    render_rc_audit,
    render_rc_audit_json,
    run_rc_audit,
)


def test_rc_audit_runs():
    report = run_rc_audit()
    assert isinstance(report, RcAuditReport)


def test_rc_audit_passes():
    report = run_rc_audit()
    assert report.verdict != "fail", (
        "rc audit failed:\n" + "\n".join(report.errors)
    )


def test_rc_audit_returns_checks():
    report = run_rc_audit()
    assert report.checks


def test_rc_audit_json_parses():
    report = run_rc_audit()
    raw = render_rc_audit_json(report)
    parsed = json.loads(raw)
    assert "version" in parsed
    assert "codename" in parsed
    assert "collected_at" in parsed
    assert "checks" in parsed
    assert "warnings" in parsed
    assert "errors" in parsed
    assert "verdict" in parsed
    assert "safety" in parsed


def test_rc_audit_json_version_field():
    import pipetune
    report = run_rc_audit()
    parsed = json.loads(render_rc_audit_json(report))
    assert parsed["version"] == pipetune.__version__
    assert parsed["version"] == "1.0.0rc1"


def test_rc_audit_json_safety_block():
    report = run_rc_audit()
    parsed = json.loads(render_rc_audit_json(report))
    safety = parsed["safety"]
    assert safety["read_only"] is True
    assert safety["modified_system"] is False
    assert safety["changed_routing"] is False
    assert safety["restarted_services"] is False
    assert safety["wrote_user_audio_config"] is False


def test_rc_audit_text_render():
    report = run_rc_audit()
    text = render_rc_audit(report)
    assert "PipeTune RC Audit" in text
    assert "Verdict:" in text
    assert "No audio routing was changed." in text


def test_rc_audit_checks_version_metadata():
    report = run_rc_audit()
    assert any("1.0.0rc1" in check for check in report.checks), (
        "rc audit should confirm version metadata"
    )


def test_rc_audit_checks_required_docs():
    report = run_rc_audit()
    assert any("doc exists:" in check for check in report.checks)


def test_rc_audit_checks_command_groups():
    report = run_rc_audit()
    assert any("command group available" in check for check in report.checks)


def test_rc_audit_checks_no_forbidden_attribution():
    report = run_rc_audit()
    assert any("forbidden attribution" in check for check in report.checks), (
        "rc audit should confirm no forbidden attribution text"
    )


def test_rc_audit_is_read_only():
    report = run_rc_audit()
    parsed = json.loads(render_rc_audit_json(report))
    assert parsed["safety"]["read_only"] is True
    assert parsed["safety"]["modified_system"] is False
