"""Profile database listing and search for PipeTune Linux."""

from __future__ import annotations

from pathlib import Path

from pipetune.profiles.loader import ProfileRecord, load_all_profiles
from pipetune.profiles.schema import QUALITY_CLASS_DESCRIPTIONS, SAFETY_STATUS_DESCRIPTIONS
from pipetune.profiles.validator import PACKAGE_SAFETY_DISCLAIMER


def list_profiles(
    profile_type: str | None = None,
    quality_class: str | None = None,
    db_root: Path | None = None,
) -> list[ProfileRecord]:
    profiles = [p for p in load_all_profiles(db_root) if not p.parse_error]
    if profile_type:
        profiles = [p for p in profiles if p.profile_type == profile_type]
    if quality_class:
        profiles = [p for p in profiles if p.quality_class == quality_class.upper()]
    return profiles


def show_profile(profile_id: str, db_root: Path | None = None) -> ProfileRecord | None:
    for profile in load_all_profiles(db_root):
        if profile.profile_id == profile_id:
            return profile
    return None


def search_profiles(query: str, db_root: Path | None = None) -> list[ProfileRecord]:
    query_lower = query.lower()
    results: list[ProfileRecord] = []
    for profile in load_all_profiles(db_root):
        if profile.parse_error:
            continue
        searchable = " ".join([
            profile.profile_id,
            profile.profile_name,
            profile.profile_type,
            profile.device_vendor,
            profile.device_model,
            profile.metadata.get("notes", ""),
        ]).lower()
        if query_lower in searchable:
            results.append(profile)
    return results


def render_profile_list(profiles: list[ProfileRecord]) -> str:
    if not profiles:
        lines = ["No profiles found.", "", *PACKAGE_SAFETY_DISCLAIMER]
        return "\n".join(lines)
    lines = [f"Profile Database — {len(profiles)} profile(s)", ""]
    for profile in profiles:
        qc_desc = QUALITY_CLASS_DESCRIPTIONS.get(profile.quality_class, "unknown")
        lines.append(f"  {profile.profile_id}")
        lines.append(f"    Name:    {profile.profile_name}")
        lines.append(f"    Type:    {profile.profile_type}")
        lines.append(f"    Quality: {profile.quality_class} — {qc_desc}")
        lines.append(f"    Status:  {profile.safety_status}")
        lines.append(f"    Vendor:  {profile.device_vendor} {profile.device_model}")
        lines.append("")
    lines.extend(PACKAGE_SAFETY_DISCLAIMER)
    return "\n".join(lines)


def render_profile_detail(profile: ProfileRecord) -> str:
    if profile.parse_error:
        return f"Profile {profile.path.name} could not be parsed: {profile.parse_error}"
    qc_desc = QUALITY_CLASS_DESCRIPTIONS.get(profile.quality_class, "unknown")
    ss_desc = SAFETY_STATUS_DESCRIPTIONS.get(profile.safety_status, "unknown")
    lines = [
        f"Profile: {profile.profile_id}",
        "",
        f"  Name:          {profile.profile_name}",
        f"  Type:          {profile.profile_type}",
        f"  Version:       {profile.metadata.get('version', '')}",
        f"  Vendor:        {profile.device_vendor}",
        f"  Model:         {profile.device_model}",
        f"  Category:      {profile.metadata.get('device_category', '')}",
        f"  Source type:   {profile.metadata.get('source_type', '')}",
    ]
    if profile.metadata.get("source_url"):
        lines.append(f"  Source URL:    {profile.metadata['source_url']}")
    if profile.metadata.get("source_reference"):
        lines.append(f"  Source ref:    {profile.metadata['source_reference']}")
    lines.extend([
        f"  License:       {profile.metadata.get('license', '')}",
        f"  Quality:       {profile.quality_class} — {qc_desc}",
        f"  Safety status: {profile.safety_status} — {ss_desc}",
        f"  Created:       {profile.metadata.get('created_at', profile.metadata.get('updated_at', ''))}",
        f"  Maintainer:    {profile.metadata.get('maintainer', '')}",
        f"  Notes:         {profile.metadata.get('notes', '')}",
    ])
    safeguards = profile.raw.get("safeguards")
    if safeguards:
        lines.append("")
        lines.append("  Safeguards:")
        for k, v in safeguards.items():
            lines.append(f"    {k}: {v}")
    lines.extend(["", *PACKAGE_SAFETY_DISCLAIMER])
    return "\n".join(lines)
