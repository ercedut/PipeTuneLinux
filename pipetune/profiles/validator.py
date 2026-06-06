"""Profile database validation for PipeTune Linux."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from pipetune.profiles.loader import ProfileRecord, load_all_profiles
from pipetune.profiles.schema import (
    REQUIRED_METADATA_FIELDS,
    VALID_PROFILE_TYPES,
    VALID_QUALITY_CLASSES,
    VALID_SAFETY_STATUSES,
)

PACKAGE_SAFETY_DISCLAIMER = [
    "No profile was installed or applied.",
    "No global LV2 installation was performed.",
    "No audio routing was changed.",
    "No PipeWire, WirePlumber, ALSA, service, system, or user audio configuration was modified.",
]


@dataclass(slots=True)
class ProfileDbReport:
    passed: bool
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


def run_profile_db_validation(db_root: Path | None = None) -> ProfileDbReport:
    checks: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []

    profiles = load_all_profiles(db_root)

    if not profiles:
        warnings.append("profile database is empty — no .toml files found")
        return ProfileDbReport(passed=True, checks=checks, warnings=warnings, errors=errors)

    checks.append(f"profile database found: {len(profiles)} profile(s)")

    seen_ids: dict[str, str] = {}
    device_combinations: dict[tuple[str, str, str], list[str]] = {}

    for profile in profiles:
        rel = profile.path.name

        if profile.parse_error:
            errors.append(f"parse error in {rel}: {profile.parse_error}")
            continue

        checks.append(f"parsed: {rel}")

        _validate_required_fields(profile, rel, checks, errors)
        _validate_known_values(profile, rel, checks, errors)
        _validate_source_and_license(profile, rel, checks, errors)
        _validate_laptop_speaker_safeguards(profile, rel, checks, errors)
        _validate_measurement_correction(profile, rel, warnings)

        pid = profile.profile_id
        if pid:
            if pid in seen_ids:
                errors.append(f"duplicate profile_id '{pid}' in {rel} (already seen in {seen_ids[pid]})")
            else:
                seen_ids[pid] = rel
                checks.append(f"profile_id unique: {pid}")

        if profile.device_vendor and profile.device_model and profile.profile_type:
            key = (profile.device_vendor, profile.device_model, profile.profile_type)
            device_combinations.setdefault(key, []).append(rel)

    for key, paths in device_combinations.items():
        if len(paths) > 1:
            warnings.append(
                f"multiple profiles for {key[0]} {key[1]} ({key[2]}): "
                + ", ".join(paths)
                + " — ensure they are versioned differently"
            )

    return ProfileDbReport(passed=not errors, checks=checks, warnings=warnings, errors=errors)


def _validate_required_fields(
    profile: ProfileRecord, rel: str, checks: list[str], errors: list[str]
) -> None:
    for field_name in REQUIRED_METADATA_FIELDS:
        if field_name not in profile.metadata or not profile.metadata[field_name]:
            errors.append(f"missing required metadata field '{field_name}' in {rel}")
        else:
            checks.append(f"  {rel}: field present: {field_name}")


def _validate_known_values(
    profile: ProfileRecord, rel: str, checks: list[str], errors: list[str]
) -> None:
    pt = profile.profile_type
    if pt and pt not in VALID_PROFILE_TYPES:
        errors.append(f"unknown profile_type '{pt}' in {rel} (allowed: {sorted(VALID_PROFILE_TYPES)})")
    elif pt:
        checks.append(f"  {rel}: profile_type valid: {pt}")

    qc = profile.quality_class
    if qc and qc not in VALID_QUALITY_CLASSES:
        errors.append(f"unknown quality_class '{qc}' in {rel} (allowed: A, B, C, D)")
    elif qc:
        checks.append(f"  {rel}: quality_class valid: {qc}")

    ss = profile.safety_status
    if ss and ss not in VALID_SAFETY_STATUSES:
        errors.append(f"unknown safety_status '{ss}' in {rel} (allowed: {sorted(VALID_SAFETY_STATUSES)})")
    elif ss:
        checks.append(f"  {rel}: safety_status valid: {ss}")


def _validate_source_and_license(
    profile: ProfileRecord, rel: str, checks: list[str], errors: list[str]
) -> None:
    if not profile.has_source():
        errors.append(f"missing source (source_url or source_reference) in {rel}")
    else:
        checks.append(f"  {rel}: source present")

    if not profile.metadata.get("license"):
        errors.append(f"missing license field in {rel}")
    else:
        checks.append(f"  {rel}: license present: {profile.metadata['license']}")


def _validate_laptop_speaker_safeguards(
    profile: ProfileRecord, rel: str, checks: list[str], errors: list[str]
) -> None:
    if profile.profile_type != "laptop-speaker":
        return
    sg = profile.raw.get("safeguards", {})
    if sg.get("hpf_hz") is None:
        errors.append(f"laptop-speaker profile missing safeguards.hpf_hz in {rel}")
    else:
        checks.append(f"  {rel}: safeguards.hpf_hz present: {sg['hpf_hz']} Hz")
    if sg.get("limiter_ceiling_db") is None:
        errors.append(f"laptop-speaker profile missing safeguards.limiter_ceiling_db in {rel}")
    else:
        checks.append(f"  {rel}: safeguards.limiter_ceiling_db present: {sg['limiter_ceiling_db']} dB")


def _validate_measurement_correction(
    profile: ProfileRecord, rel: str, warnings: list[str]
) -> None:
    if profile.profile_type == "measurement-correction" and profile.safety_status not in ("draft", "rejected"):
        warnings.append(
            f"measurement-correction profile '{rel}' has safety_status='{profile.safety_status}'; "
            "should be 'draft' until manually reviewed"
        )


def render_profile_db_report(report: ProfileDbReport) -> str:
    lines = ["PipeTune Profile Database Validation", "", "Checks:"]
    if report.checks:
        for check in report.checks:
            if check.startswith("  "):
                pass
            else:
                lines.append(f"- pass: {check}")
    else:
        lines.append("- none")
    if report.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- warn: {w}" for w in report.warnings)
    if report.errors:
        lines.extend(["", "Errors:"])
        lines.extend(f"- fail: {e}" for e in report.errors)
    lines.extend(["", f"Final verdict: {report.verdict}", *PACKAGE_SAFETY_DISCLAIMER])
    return "\n".join(lines)


def render_profile_db_report_json(report: ProfileDbReport) -> str:
    return json.dumps(
        {
            "command": "profiles validate-db",
            "verdict": report.verdict,
            "passed": report.passed,
            "checks": [c for c in report.checks if not c.startswith("  ")],
            "warnings": report.warnings,
            "errors": report.errors,
        },
        indent=2,
    )
