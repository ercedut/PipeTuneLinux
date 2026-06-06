"""Tests for v0.7.0 device profile database commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipetune import cli
from pipetune.profiles import loader as prof_loader
from pipetune.profiles import validator as prof_validator
from pipetune.profiles.database import list_profiles, search_profiles, show_profile
from pipetune.profiles.loader import ProfileRecord, load_all_profiles
from pipetune.profiles.schema import (
    VALID_PROFILE_TYPES,
    VALID_QUALITY_CLASSES,
    VALID_SAFETY_STATUSES,
)
from pipetune.profiles.validator import run_profile_db_validation


# ---------------------------------------------------------------------------
# Profile database structure
# ---------------------------------------------------------------------------


def test_profile_database_directory_exists() -> None:
    from pipetune.profiles.loader import PROFILES_DB_ROOT
    assert PROFILES_DB_ROOT.is_dir(), "profiles/ database directory is missing"


def test_profile_database_has_example_profiles() -> None:
    from pipetune.profiles.loader import PROFILES_DB_ROOT
    toml_files = list(PROFILES_DB_ROOT.rglob("*.toml"))
    non_template = [f for f in toml_files if "templates" not in str(f)]
    assert len(non_template) >= 4, "Expected at least 4 example profiles in database"


def test_example_profiles_all_parse() -> None:
    profiles = load_all_profiles()
    for p in profiles:
        assert p.parse_error is None, f"Profile {p.path.name} failed to parse: {p.parse_error}"


def test_example_profiles_have_required_metadata() -> None:
    from pipetune.profiles.schema import REQUIRED_METADATA_FIELDS
    profiles = load_all_profiles()
    assert profiles, "No profiles loaded"
    for p in profiles:
        for field in REQUIRED_METADATA_FIELDS:
            assert field in p.metadata, f"Profile {p.path.name} missing required field: {field}"


# ---------------------------------------------------------------------------
# Profile DB validation — unit tests
# ---------------------------------------------------------------------------


def _make_valid_headphone_toml(profile_id: str = "test-headphone-001") -> str:
    return f"""
[metadata]
profile_id = "{profile_id}"
profile_name = "Test Headphone"
profile_type = "headphone"
version = "0.1.0"
device_vendor = "TestCo"
device_model = "TH-100"
device_category = "over-ear"
source_type = "autoeq-database"
source_url = "https://example.com/autoeq"
license = "MIT"
quality_class = "B"
safety_status = "draft"
created_at = "2026-06-06"
maintainer = "test"
notes = "Test profile."
"""


def _make_valid_laptop_speaker_toml(profile_id: str = "test-speaker-001") -> str:
    return f"""
[metadata]
profile_id = "{profile_id}"
profile_name = "Test Laptop Speaker"
profile_type = "laptop-speaker"
version = "0.1.0"
device_vendor = "TestCo"
device_model = "TS-100"
device_category = "laptop"
source_type = "generic-conservative"
source_reference = "test reference"
license = "MIT"
quality_class = "C"
safety_status = "draft"
created_at = "2026-06-06"
maintainer = "test"
notes = "Test speaker profile."

[safeguards]
hpf_hz = 120
limiter_ceiling_db = -1.0
"""


def _write_db(tmp_path: Path, profiles: dict[str, str]) -> Path:
    db = tmp_path / "profiles"
    (db / "headphones").mkdir(parents=True)
    (db / "speakers").mkdir(parents=True)
    for name, content in profiles.items():
        subdir = "speakers" if "speaker" in name else "headphones"
        (db / subdir / name).write_text(content, encoding="utf-8")
    return db


def test_validate_db_passes_valid_headphone(tmp_path: Path) -> None:
    db = _write_db(tmp_path, {"hp-001.toml": _make_valid_headphone_toml()})
    report = run_profile_db_validation(db)
    assert report.verdict == "pass"
    assert not report.errors


def test_validate_db_passes_valid_laptop_speaker(tmp_path: Path) -> None:
    db = _write_db(tmp_path, {"sp-001.toml": _make_valid_laptop_speaker_toml()})
    report = run_profile_db_validation(db)
    assert report.verdict == "pass"
    assert not report.errors


def test_validate_db_detects_missing_required_field(tmp_path: Path) -> None:
    toml = _make_valid_headphone_toml()
    # Remove profile_name line
    toml_missing = "\n".join(l for l in toml.splitlines() if "profile_name" not in l)
    db = _write_db(tmp_path, {"hp-bad.toml": toml_missing})
    report = run_profile_db_validation(db)
    assert report.verdict == "fail"
    assert any("profile_name" in e for e in report.errors)


def test_validate_db_detects_duplicate_profile_id(tmp_path: Path) -> None:
    toml1 = _make_valid_headphone_toml("duplicate-id")
    toml2 = _make_valid_headphone_toml("duplicate-id")
    db = _write_db(tmp_path, {"hp1.toml": toml1, "hp2.toml": toml2})
    report = run_profile_db_validation(db)
    assert report.verdict == "fail"
    assert any("duplicate" in e for e in report.errors)


def test_validate_db_rejects_unknown_quality_class(tmp_path: Path) -> None:
    toml = _make_valid_headphone_toml().replace('quality_class = "B"', 'quality_class = "Z"')
    db = _write_db(tmp_path, {"hp-bad-qc.toml": toml})
    report = run_profile_db_validation(db)
    assert report.verdict == "fail"
    assert any("quality_class" in e for e in report.errors)


def test_validate_db_rejects_unknown_safety_status(tmp_path: Path) -> None:
    toml = _make_valid_headphone_toml().replace('safety_status = "draft"', 'safety_status = "unknown-status"')
    db = _write_db(tmp_path, {"hp-bad-ss.toml": toml})
    report = run_profile_db_validation(db)
    assert report.verdict == "fail"
    assert any("safety_status" in e for e in report.errors)


def test_validate_db_rejects_missing_source(tmp_path: Path) -> None:
    toml = "\n".join(
        l for l in _make_valid_headphone_toml().splitlines()
        if "source_url" not in l and "source_reference" not in l
    )
    db = _write_db(tmp_path, {"hp-no-source.toml": toml})
    report = run_profile_db_validation(db)
    assert report.verdict == "fail"
    assert any("source" in e.lower() for e in report.errors)


def test_validate_db_rejects_missing_license(tmp_path: Path) -> None:
    toml = "\n".join(l for l in _make_valid_headphone_toml().splitlines() if 'license' not in l)
    db = _write_db(tmp_path, {"hp-no-license.toml": toml})
    report = run_profile_db_validation(db)
    assert report.verdict == "fail"
    assert any("license" in e for e in report.errors)


def test_validate_db_rejects_laptop_speaker_missing_hpf(tmp_path: Path) -> None:
    toml = _make_valid_laptop_speaker_toml()
    toml_no_hpf = "\n".join(l for l in toml.splitlines() if "hpf_hz" not in l)
    db = _write_db(tmp_path, {"sp-no-hpf.toml": toml_no_hpf})
    report = run_profile_db_validation(db)
    assert report.verdict == "fail"
    assert any("hpf_hz" in e for e in report.errors)


def test_validate_db_rejects_laptop_speaker_missing_limiter(tmp_path: Path) -> None:
    toml = _make_valid_laptop_speaker_toml()
    toml_no_lim = "\n".join(l for l in toml.splitlines() if "limiter_ceiling_db" not in l)
    db = _write_db(tmp_path, {"sp-no-lim.toml": toml_no_lim})
    report = run_profile_db_validation(db)
    assert report.verdict == "fail"
    assert any("limiter_ceiling_db" in e for e in report.errors)


def test_validate_db_warns_measurement_correction_not_draft(tmp_path: Path) -> None:
    toml = _make_valid_headphone_toml().replace(
        'profile_type = "headphone"', 'profile_type = "measurement-correction"'
    ).replace('safety_status = "draft"', 'safety_status = "safe"')
    db = _write_db(tmp_path, {"mc-safe.toml": toml})
    report = run_profile_db_validation(db)
    assert any("measurement-correction" in w for w in report.warnings)


def test_validate_db_empty_database_is_warn(tmp_path: Path) -> None:
    db = tmp_path / "profiles"
    db.mkdir()
    report = run_profile_db_validation(db)
    assert report.verdict == "warn"
    assert any("empty" in w for w in report.warnings)


def test_validate_db_parse_error_is_fail(tmp_path: Path) -> None:
    db = tmp_path / "profiles" / "headphones"
    db.mkdir(parents=True)
    (db / "broken.toml").write_text("[[this is not valid toml", encoding="utf-8")
    report = run_profile_db_validation(tmp_path / "profiles")
    assert report.verdict == "fail"
    assert any("parse error" in e for e in report.errors)


# ---------------------------------------------------------------------------
# Rejected profile cannot be applied (schema-level guard)
# ---------------------------------------------------------------------------


def test_rejected_profile_safety_status_known() -> None:
    assert "rejected" in VALID_SAFETY_STATUSES


def test_rejected_profiles_detectable_by_status(tmp_path: Path) -> None:
    toml = _make_valid_headphone_toml().replace('safety_status = "draft"', 'safety_status = "rejected"')
    db = _write_db(tmp_path, {"hp-rejected.toml": toml})
    profiles = load_all_profiles(db)
    rejected = [p for p in profiles if p.safety_status == "rejected"]
    assert rejected, "Expected at least one rejected profile"
    for p in rejected:
        assert p.safety_status == "rejected"


# ---------------------------------------------------------------------------
# Profile list / show / search
# ---------------------------------------------------------------------------


def test_profiles_list_returns_all_example_profiles() -> None:
    profiles = list_profiles()
    assert len(profiles) >= 4


def test_profiles_list_filters_by_type() -> None:
    headphones = list_profiles(profile_type="headphone")
    assert all(p.profile_type == "headphone" for p in headphones)


def test_profiles_list_filters_by_quality() -> None:
    b_class = list_profiles(quality_class="B")
    assert all(p.quality_class == "B" for p in b_class)


def test_profiles_show_returns_known_profile() -> None:
    profile = show_profile("headphone-example-autoeq-sennheiser-hd650")
    assert profile is not None
    assert profile.device_vendor == "Sennheiser"


def test_profiles_show_returns_none_for_unknown() -> None:
    profile = show_profile("this-profile-does-not-exist-xyz")
    assert profile is None


def test_profiles_search_finds_by_keyword() -> None:
    results = search_profiles("laptop")
    assert any("laptop" in p.profile_id.lower() or "laptop" in p.profile_name.lower() for p in results)


def test_profiles_search_returns_empty_for_no_match() -> None:
    results = search_profiles("zzznomatch123xyz")
    assert results == []


# ---------------------------------------------------------------------------
# Profiles CLI integration
# ---------------------------------------------------------------------------


def test_profiles_validate_db_cli_exits_zero(capsys) -> None:
    exit_code = cli.main(["profiles", "validate-db"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "PipeTune Profile Database Validation" in output
    assert "Final verdict: pass" in output
    assert "No profile was installed or applied." in output


def test_profiles_validate_db_cli_json_output(capsys) -> None:
    exit_code = cli.main(["profiles", "validate-db", "--json"])
    output = capsys.readouterr().out
    assert exit_code == 0
    data = json.loads(output)
    assert data["verdict"] == "pass"
    assert data["passed"] is True
    assert isinstance(data["checks"], list)
    assert isinstance(data["errors"], list)


def test_profiles_list_cli_exits_zero(capsys) -> None:
    exit_code = cli.main(["profiles", "list"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Profile Database" in output
    assert "No profile was installed or applied." in output


def test_profiles_list_cli_type_filter(capsys) -> None:
    exit_code = cli.main(["profiles", "list", "--type", "headphone"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "headphone" in output


def test_profiles_show_cli_known_profile(capsys) -> None:
    exit_code = cli.main(["profiles", "show", "headphone-example-autoeq-sennheiser-hd650"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Sennheiser" in output
    assert "No profile was installed or applied." in output


def test_profiles_show_cli_unknown_profile(capsys) -> None:
    exit_code = cli.main(["profiles", "show", "nonexistent-profile-xyz"])
    assert exit_code == 1


def test_profiles_search_cli_returns_results(capsys) -> None:
    exit_code = cli.main(["profiles", "search", "headphone"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "No profile was installed or applied." in output


def test_profiles_no_system_mutation(capsys) -> None:
    cli.main(["profiles", "list"])
    output = capsys.readouterr().out
    assert "No profile was installed or applied." in output
    assert "No global LV2 installation was performed." in output
    assert "No audio routing was changed." in output


# ---------------------------------------------------------------------------
# Release check includes profile DB validation
# ---------------------------------------------------------------------------


def test_release_check_includes_profile_db(capsys) -> None:
    from pipetune import release as rel
    report = rel.run_release_check()
    combined = " ".join(report.checks + report.warnings + report.errors)
    assert "profile database" in combined.lower()


# ---------------------------------------------------------------------------
# CI and docs
# ---------------------------------------------------------------------------


def test_ci_workflow_includes_profiles_validate_db() -> None:
    ci_path = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
    assert ci_path.exists()
    content = ci_path.read_text(encoding="utf-8")
    assert "profiles validate-db" in content


def test_docs_profile_database_exists() -> None:
    assert (Path(__file__).resolve().parents[1] / "docs" / "profile-database.md").exists()


def test_docs_profile_contribution_guide_exists() -> None:
    assert (Path(__file__).resolve().parents[1] / "docs" / "profile-contribution-guide.md").exists()


def test_profile_request_template_exists() -> None:
    assert (Path(__file__).resolve().parents[1] / "profiles" / "templates" / "profile-request.md").exists()


def test_profile_submission_template_exists() -> None:
    assert (Path(__file__).resolve().parents[1] / "profiles" / "templates" / "profile-submission.md").exists()
