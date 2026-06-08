"""Tests: rc mutation-audit."""

import json
import tempfile
from pathlib import Path

from pipetune.rc.mutation_audit import (
    render_mutation_audit,
    render_mutation_audit_json,
    run_mutation_audit,
)


def test_mutation_audit_current_source_passes():
    report = run_mutation_audit()
    assert report.verdict != "fail", (
        f"mutation audit failed on current source:\n" + "\n".join(report.errors)
    )


def test_mutation_audit_returns_checks():
    report = run_mutation_audit()
    assert report.checks


def test_mutation_audit_json_parses():
    report = run_mutation_audit()
    raw = render_mutation_audit_json(report)
    parsed = json.loads(raw)
    assert "verdict" in parsed
    assert "passed" in parsed
    assert "findings" in parsed
    assert "safety" in parsed


def test_mutation_audit_json_safety_block():
    report = run_mutation_audit()
    parsed = json.loads(render_mutation_audit_json(report))
    safety = parsed["safety"]
    assert safety["read_only"] is True
    assert safety["modified_system"] is False
    assert safety["changed_routing"] is False
    assert safety["restarted_services"] is False
    assert safety["wrote_user_audio_config"] is False


def test_mutation_audit_text_render():
    report = run_mutation_audit()
    text = render_mutation_audit(report)
    assert "RC Mutation Audit" in text
    assert "Verdict:" in text


def test_mutation_audit_detects_dangerous_production_pattern():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        prod_dir = root / "pipetune"
        prod_dir.mkdir()
        dangerous_file = prod_dir / "bad_module.py"
        dangerous_file.write_text(
            'subprocess.run(["systemctl", "restart", "wireplumber"])\n',
            encoding="utf-8",
        )
        report = run_mutation_audit(root=root)
        assert report.verdict == "fail"
        assert any("dangerous" in e.lower() or "systemctl restart" in e.lower() for e in report.errors)


def test_mutation_audit_docs_only_warning_not_error():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        docs_dir = root / "docs"
        docs_dir.mkdir()
        doc_file = docs_dir / "example.md"
        doc_file.write_text(
            "Example: subprocess.run(['systemctl', 'restart', 'wireplumber'])\n",
            encoding="utf-8",
        )
        pipetune_dir = root / "pipetune"
        pipetune_dir.mkdir()
        (pipetune_dir / "safe.py").write_text("# safe module\nx = 1\n", encoding="utf-8")
        report = run_mutation_audit(root=root)
        assert report.verdict != "fail", "docs-only pattern should not be a fail"
        assert any("systemctl" in w.lower() or "restart" in w.lower() for w in report.warnings), (
            "subprocess restart pattern in docs should produce a warning"
        )


def test_mutation_audit_no_findings_on_clean_source():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        prod_dir = root / "pipetune"
        prod_dir.mkdir()
        (prod_dir / "clean.py").write_text("x = 1\nprint(x)\n", encoding="utf-8")
        report = run_mutation_audit(root=root)
        assert report.verdict == "pass"
        assert not report.errors
