"""Generated profile manifest support."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pipetune.safety.metadata import analyze_config_text, build_profile_metadata, manifest_path_for_config, validate_profile_type


def create_profile_manifest(config_file: Path, profile_name: str, profile_type: str) -> tuple[Path | None, dict[str, Any] | None, list[str]]:
    if not validate_profile_type(profile_type):
        return None, None, [f"Invalid profile type: {profile_type}"]
    if not config_file.exists() or not config_file.is_file():
        return None, None, [f"Config file not found: {config_file}"]

    try:
        text = config_file.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return None, None, [f"Config file could not be read: {exc}"]

    metadata = build_profile_metadata(config_file, profile_name, profile_type, text)
    analysis = analyze_config_text(text)
    manifest = {
        "schema_version": 1,
        "config_file": str(config_file),
        "appears_generated_by_pipetune": bool(analysis["appears_generated_by_pipetune"]),
        "filter_labels": analysis["filter_labels"],
        "profile": metadata.to_dict(),
        "safety": {
            "auto_apply_safe": metadata.auto_apply_safe,
            "requires_manual_output_confirmation": metadata.requires_manual_output_confirmation,
            "hardware_quirk_sensitive": metadata.hardware_quirk_sensitive,
            "warnings": metadata.warnings,
        },
    }

    output_path = manifest_path_for_config(config_file)
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return output_path, manifest, []


def load_manifest_for_config(config_file: Path) -> dict[str, Any] | None:
    path = manifest_path_for_config(config_file)
    if not path.exists() or not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def render_manifest_result(path: Path | None, errors: list[str]) -> str:
    if errors:
        lines = ["PipeTune Profile Manifest", "", "Errors:"]
        lines.extend(f"* {error}" for error in errors)
        lines.extend(["", "No system configuration was modified."])
        return "\n".join(lines)

    lines = [
        "PipeTune Profile Manifest",
        "",
        f"Manifest: {path}",
        "",
        "No system configuration was modified.",
    ]
    return "\n".join(lines)
