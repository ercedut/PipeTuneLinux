"""Tests: release check includes rc gates."""

import tempfile
from pathlib import Path

from pipetune.release import run_release_check
from pipetune.rc.mutation_audit import run_mutation_audit
from pipetune.rc.docs_check import run_docs_check


def test_release_check_passes():
    report = run_release_check()
    assert report.verdict != "fail", (
        "release check failed:\n" + "\n".join(report.errors)
    )


def test_release_check_includes_rc_mutation_audit():
    report = run_release_check()
    all_messages = report.checks + report.warnings + report.errors
    assert any("mutation" in m.lower() for m in all_messages), (
        "release check should include rc mutation-audit results"
    )


def test_release_check_includes_rc_docs_check():
    report = run_release_check()
    all_messages = report.checks + report.warnings + report.errors
    assert any("docs-check" in m.lower() or "docs check" in m.lower() for m in all_messages), (
        "release check should include rc docs-check results"
    )


def test_release_check_fails_if_mutation_audit_fails():
    with tempfile.TemporaryDirectory() as tmp:
        from unittest.mock import patch
        from pipetune.rc.mutation_audit import MutationAuditReport
        bad_report = MutationAuditReport(
            checks=[],
            warnings=[],
            errors=["DANGEROUS pattern in production source pipetune/bad.py:1: service restart call"],
        )
        with patch("pipetune.release.run_mutation_audit", return_value=bad_report):
            report = run_release_check()
        assert report.verdict == "fail"
        assert any("mutation" in e.lower() for e in report.errors)


def test_release_check_fails_if_docs_check_fails():
    from unittest.mock import patch
    from pipetune.rc.docs_check import DocsCheckReport
    bad_report = DocsCheckReport(
        checks=[],
        warnings=[],
        errors=["required doc missing: docs/release-candidate.md"],
    )
    with patch("pipetune.release.run_docs_check", return_value=bad_report):
        report = run_release_check()
    assert report.verdict == "fail"
    assert any("docs-check" in e.lower() for e in report.errors)


def test_mutation_audit_passes_current_source():
    report = run_mutation_audit()
    assert report.verdict != "fail"


def test_docs_check_passes_current_docs():
    report = run_docs_check()
    assert report.verdict != "fail"
