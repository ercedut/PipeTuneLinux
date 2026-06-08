"""Tests: rc docs-check."""

import json
import tempfile
from pathlib import Path

from pipetune.rc.docs_check import (
    render_docs_check,
    render_docs_check_json,
    run_docs_check,
)


def test_docs_check_passes_current_docs():
    report = run_docs_check()
    assert report.verdict != "fail", (
        "docs-check failed on current docs:\n" + "\n".join(report.errors)
    )


def test_docs_check_returns_checks():
    report = run_docs_check()
    assert report.checks


def test_docs_check_json_parses():
    report = run_docs_check()
    raw = render_docs_check_json(report)
    parsed = json.loads(raw)
    assert "verdict" in parsed
    assert "passed" in parsed
    assert "checks" in parsed
    assert "errors" in parsed
    assert "safety" in parsed


def test_docs_check_json_safety_block():
    report = run_docs_check()
    parsed = json.loads(render_docs_check_json(report))
    safety = parsed["safety"]
    assert safety["read_only"] is True
    assert safety["modified_system"] is False
    assert safety["changed_routing"] is False
    assert safety["restarted_services"] is False
    assert safety["wrote_user_audio_config"] is False


def test_docs_check_text_render():
    report = run_docs_check()
    text = render_docs_check(report)
    assert "RC Docs Check" in text
    assert "Verdict:" in text


def test_docs_check_catches_missing_referenced_doc():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "README.md").write_text(
            "# PipeTune Linux v1.0.0-rc1\n\nSee [docs/nonexistent.md](docs/nonexistent.md).\n",
            encoding="utf-8",
        )
        (root / "CHANGELOG.md").write_text("# Changelog\n\n## [1.0.0-rc1] - 2026-06-09\n", encoding="utf-8")
        docs_dir = root / "docs"
        docs_dir.mkdir()
        (docs_dir / "roadmap.md").write_text("## v1.0.0-rc1 (Current)\n", encoding="utf-8")
        (docs_dir / "release-checklist.md").write_text(
            "rc audit\nmutation-audit\nfedora-smoke\nforbidden attribution\ncompiled artifact\ngenerated preview artifact\ndirty release check\n",
            encoding="utf-8",
        )
        (docs_dir / "release-candidate.md").write_text("# RC\n", encoding="utf-8")
        (docs_dir / "install.md").write_text("pip install -e .\n", encoding="utf-8")
        report = run_docs_check(root=root)
        assert any("nonexistent" in e or "broken internal link" in e for e in report.errors), (
            "Should fail because docs/nonexistent.md is linked from README but does not exist"
        )


def test_docs_check_readme_missing_version_fails():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "README.md").write_text("# PipeTune Linux\n\nOld docs.\n", encoding="utf-8")
        (root / "CHANGELOG.md").write_text("# Changelog\n\n## [1.0.0-rc1] - 2026-06-09\n", encoding="utf-8")
        docs_dir = root / "docs"
        docs_dir.mkdir()
        (docs_dir / "roadmap.md").write_text("## v1.0.0-rc1 (Current)\n", encoding="utf-8")
        (docs_dir / "release-checklist.md").write_text(
            "rc audit\nmutation-audit\nfedora-smoke\nforbidden attribution\ncompiled artifact\ngenerated preview artifact\ndirty release check\n",
            encoding="utf-8",
        )
        (docs_dir / "release-candidate.md").write_text("# RC\n", encoding="utf-8")
        (docs_dir / "install.md").write_text("pip install -e .\n", encoding="utf-8")
        report = run_docs_check(root=root)
        assert any("v1.0.0-rc1" in e for e in report.errors), (
            "Should fail because README does not mention v1.0.0-rc1"
        )


def test_docs_check_catches_forbidden_attribution():
    forbidden_text = "Co-Authored" + "-By: bot"
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "README.md").write_text(
            f"# PipeTune Linux v1.0.0-rc1\n\nSee [docs/install.md](docs/install.md).\n{forbidden_text}\n",
            encoding="utf-8",
        )
        (root / "CHANGELOG.md").write_text("# Changelog\n\n## [1.0.0-rc1] - 2026-06-09\n", encoding="utf-8")
        docs_dir = root / "docs"
        docs_dir.mkdir()
        (docs_dir / "roadmap.md").write_text("## v1.0.0-rc1 (Current)\n", encoding="utf-8")
        (docs_dir / "release-checklist.md").write_text(
            "rc audit\nmutation-audit\nfedora-smoke\nforbidden attribution\ncompiled artifact\ngenerated preview artifact\ndirty release check\n",
            encoding="utf-8",
        )
        (docs_dir / "release-candidate.md").write_text("# RC\n", encoding="utf-8")
        (docs_dir / "install.md").write_text("pip install -e .\n", encoding="utf-8")
        report = run_docs_check(root=root)
        assert any("forbidden attribution" in e.lower() for e in report.errors), (
            "Should fail because README contains forbidden attribution text"
        )
