"""PipeTune Linux RC docs check — documentation integrity and consistency validation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from pipetune.packaging import REPO_ROOT

_FORBIDDEN_ATTRIBUTION_PARTS = ("Co-Authored" + "-By", "AI" + " assistant")

_MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


@dataclass(slots=True)
class DocsCheckReport:
    checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def verdict(self) -> str:
        if self.errors:
            return "fail"
        if self.warnings:
            return "warn"
        return "pass"

    @property
    def passed(self) -> bool:
        return not self.errors


def _extract_internal_links(text: str) -> list[str]:
    links = []
    for _label, target in _MARKDOWN_LINK.findall(text):
        if target.startswith("http://") or target.startswith("https://"):
            continue
        target = target.split("#")[0].strip()
        if target and not target.startswith("mailto:"):
            links.append(target)
    return links


def _check_internal_links(
    source_file: Path,
    root: Path,
    checks: list[str],
    errors: list[str],
) -> None:
    try:
        text = source_file.read_text(encoding="utf-8")
    except OSError:
        errors.append(f"cannot read {source_file.relative_to(root)}")
        return
    links = _extract_internal_links(text)
    broken = []
    for link in links:
        target = (source_file.parent / link).resolve()
        if not target.exists():
            broken.append(link)
    if broken:
        for link in broken:
            errors.append(f"broken internal link in {source_file.relative_to(root)}: {link}")
    else:
        if links:
            checks.append(f"internal links in {source_file.relative_to(root)}: all {len(links)} found")


def _check_attribution(
    file_path: Path,
    root: Path,
    checks: list[str],
    errors: list[str],
) -> None:
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError:
        return
    if any(part.lower() in text.lower() for part in _FORBIDDEN_ATTRIBUTION_PARTS):
        errors.append(f"forbidden attribution text found in {file_path.relative_to(root)}")
    else:
        checks.append(f"no forbidden attribution in {file_path.relative_to(root)}")


def run_docs_check(root: Path = REPO_ROOT) -> DocsCheckReport:
    checks: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []

    readme = root / "README.md"
    changelog = root / "CHANGELOG.md"
    roadmap = root / "docs" / "roadmap.md"
    checklist = root / "docs" / "release-checklist.md"
    install_doc = root / "docs" / "install.md"

    for path, label in [
        (readme, "README.md"),
        (changelog, "CHANGELOG.md"),
        (roadmap, "docs/roadmap.md"),
        (checklist, "docs/release-checklist.md"),
        (install_doc, "docs/install.md"),
    ]:
        if path.exists():
            checks.append(f"doc exists: {label}")
        else:
            errors.append(f"required doc missing: {label}")

    if readme.exists():
        readme_text = readme.read_text(encoding="utf-8")
        if "v1.0.0-rc1" in readme_text:
            checks.append("README contains v1.0.0-rc1 version marker")
        else:
            errors.append("README does not mention v1.0.0-rc1")

        _check_internal_links(readme, root, checks, errors)
        _check_attribution(readme, root, checks, errors)

    if changelog.exists():
        changelog_text = changelog.read_text(encoding="utf-8")
        if "## [1.0.0-rc1]" in changelog_text:
            checks.append("CHANGELOG contains ## [1.0.0-rc1] section")
        else:
            errors.append("CHANGELOG missing ## [1.0.0-rc1] section")
        _check_attribution(changelog, root, checks, errors)

    if roadmap.exists():
        roadmap_text = roadmap.read_text(encoding="utf-8")
        if "v1.0.0-rc1" in roadmap_text and "(Current)" in roadmap_text:
            checks.append("roadmap marks v1.0.0-rc1 as Current")
        else:
            errors.append("roadmap does not mark v1.0.0-rc1 as Current")
        _check_internal_links(roadmap, root, checks, errors)
        _check_attribution(roadmap, root, checks, errors)

    if checklist.exists():
        checklist_text = checklist.read_text(encoding="utf-8")
        required_checklist_items = [
            ("rc audit", "rc audit"),
            ("mutation-audit", "rc mutation-audit"),
            ("fedora-smoke", "rc fedora-smoke"),
            ("forbidden attribution", "no forbidden attribution text check"),
            ("compiled artifact", "no compiled artifact check"),
            ("generated preview artifact", "no generated preview artifact check"),
            ("dirty release check", "dirty release check warning"),
        ]
        for keyword, description in required_checklist_items:
            if keyword in checklist_text:
                checks.append(f"release-checklist mentions: {description}")
            else:
                errors.append(f"release-checklist missing mention of: {description}")
        _check_internal_links(checklist, root, checks, errors)
        _check_attribution(checklist, root, checks, errors)

    if install_doc.exists():
        install_text = install_doc.read_text(encoding="utf-8")
        if "pip install -e" in install_text or "editable" in install_text.lower():
            checks.append("install.md mentions editable install")
        else:
            warnings.append("install.md may not mention editable install explicitly")
        _check_attribution(install_doc, root, checks, errors)

    rc_doc = root / "docs" / "release-candidate.md"
    if rc_doc.exists():
        checks.append("docs/release-candidate.md exists")
        _check_internal_links(rc_doc, root, checks, errors)
        _check_attribution(rc_doc, root, checks, errors)
    else:
        errors.append("docs/release-candidate.md is missing")

    for doc in sorted((root / "docs").glob("*.md")) if (root / "docs").is_dir() else []:
        rel = str(doc.relative_to(root))
        try:
            text = doc.read_text(encoding="utf-8")
        except OSError:
            continue
        if any(part.lower() in text.lower() for part in _FORBIDDEN_ATTRIBUTION_PARTS):
            errors.append(f"forbidden attribution text in {rel}")

    return DocsCheckReport(checks=checks, warnings=warnings, errors=errors)


def render_docs_check(report: DocsCheckReport) -> str:
    lines = ["PipeTune RC Docs Check", ""]
    lines.append("Checks:")
    for check in report.checks:
        lines.append(f"- pass: {check}")
    if not report.checks:
        lines.append("- none")
    if report.warnings:
        lines.extend(["", "Warnings:"])
        for warning in report.warnings:
            lines.append(f"- warn: {warning}")
    if report.errors:
        lines.extend(["", "Errors:"])
        for error in report.errors:
            lines.append(f"- fail: {error}")
    lines.extend([
        "",
        f"Verdict: {report.verdict}",
        "",
        "No system configuration was modified.",
        "No audio routing was changed.",
    ])
    return "\n".join(lines)


def render_docs_check_json(report: DocsCheckReport) -> str:
    return json.dumps(
        {
            "verdict": report.verdict,
            "passed": report.passed,
            "checks": report.checks,
            "warnings": report.warnings,
            "errors": report.errors,
            "safety": {
                "read_only": True,
                "modified_system": False,
                "changed_routing": False,
                "restarted_services": False,
                "wrote_user_audio_config": False,
            },
        },
        indent=2,
    )
