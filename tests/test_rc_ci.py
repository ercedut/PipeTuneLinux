"""Tests: CI workflow includes rc commands and does not install bare sord."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CI_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def _ci_text() -> str:
    return CI_PATH.read_text(encoding="utf-8")


def test_ci_workflow_exists():
    assert CI_PATH.exists(), "CI workflow file not found"


def test_ci_workflow_includes_rc_audit():
    text = _ci_text()
    assert "rc audit" in text or "rc-gates" in text, "CI workflow should include rc audit"


def test_ci_workflow_includes_rc_mutation_audit():
    text = _ci_text()
    assert "rc mutation-audit" in text or "mutation-audit" in text


def test_ci_workflow_includes_rc_docs_check():
    text = _ci_text()
    assert "rc docs-check" in text or "docs-check" in text


def test_ci_workflow_includes_rc_command_matrix():
    text = _ci_text()
    assert "rc command-matrix" in text or "command-matrix" in text


def test_ci_workflow_no_bare_sord():
    text = _ci_text()
    bare_sord_pattern = re.compile(r"apt.get install[^#\n]*\bsord\b(?!-validate)")
    assert not bare_sord_pattern.search(text), (
        "CI workflow installs bare 'sord' package which does not exist on Ubuntu noble"
    )


def test_ci_workflow_no_service_restart():
    text = _ci_text()
    assert "systemctl restart" not in text, "CI should not restart services"
    assert "systemctl --user restart" not in text


def test_ci_workflow_no_routing_mutation():
    text = _ci_text()
    assert "wpctl set-default" not in text
    assert "pactl set-default-sink" not in text
    assert "pactl set-default-source" not in text


def test_ci_workflow_no_global_lv2_install():
    text = _ci_text()
    assert "plugin install" not in text.lower() or "lv2 install" not in text.lower()


def test_ci_workflow_has_release_check():
    text = _ci_text()
    assert "release check" in text


def test_ci_workflow_has_artifact_check():
    text = _ci_text()
    assert "artifact-check" in text or "artifact check" in text
