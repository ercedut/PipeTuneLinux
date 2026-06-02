"""Safe correction draft generation from normalized measurements."""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path

from pipetune import __version__
from pipetune.measurement import MeasurementError
from pipetune.measurement.response import read_normalized_response_csv, validate_response_csv

DEFAULT_MAX_BOOST_DB = 3.0
BROAD_BAND_CENTERS_HZ = [160.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0]


def generate_correction_draft(
    input_path: Path,
    output_path: Path,
    *,
    target: str = "flat",
    safe: bool = True,
    profile_type: str = "laptop-speaker",
    max_boost_db: float = DEFAULT_MAX_BOOST_DB,
) -> Path:
    if target != "flat":
        raise MeasurementError("Only target 'flat' is supported in v0.4.1.")
    if not safe:
        raise MeasurementError("Correction generation requires --safe in v0.4.1.")
    if max_boost_db > DEFAULT_MAX_BOOST_DB:
        raise MeasurementError("Unsafe boost limit: max boost must be <= 3 dB.")
    if profile_type not in {"laptop-speaker", "measurement-correction"}:
        raise MeasurementError("Profile type must be laptop-speaker or measurement-correction.")

    validation = validate_response_csv(input_path)
    if validation.measurement_quality == "fail":
        first_error = validation.errors[0] if validation.errors else "data quality is fail."
        raise MeasurementError(f"Correction refused: {first_error}")

    response = read_normalized_response_csv(input_path)
    if len(response) < 6:
        raise MeasurementError("Correction refused: at least six response points are required.")

    reference = _median([magnitude for _frequency, magnitude in response])
    filters = _draft_filters(response, reference, profile_type, max_boost_db)
    if not filters:
        raise MeasurementError("Correction refused: no useful broad correction bands were found.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    safety_report = _safety_report(input_path, filters, profile_type, max_boost_db, validation.to_dict())
    safety_report_path = output_path.with_suffix(output_path.suffix + ".safety.json")
    output_path.write_text(
        _render_toml(input_path, filters, profile_type, max_boost_db, safety_report, safety_report_path),
        encoding="utf-8",
    )
    safety_report_path.write_text(
        json.dumps(safety_report, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def _draft_filters(
    response: list[tuple[float, float]],
    reference_db: float,
    profile_type: str,
    max_boost_db: float,
) -> list[dict[str, float | str]]:
    filters: list[dict[str, float | str]] = []
    for center_hz in BROAD_BAND_CENTERS_HZ:
        values = [
            magnitude
            for frequency, magnitude in response
            if center_hz / math.sqrt(2.0) <= frequency <= center_hz * math.sqrt(2.0)
        ]
        if not values:
            continue
        average = sum(values) / len(values)
        required_gain = reference_db - average
        if profile_type == "laptop-speaker" and center_hz < 120.0 and required_gain > 0:
            continue
        if required_gain > max_boost_db:
            raise MeasurementError(
                f"Unsafe correction: {center_hz:g} Hz would require +{required_gain:.2f} dB boost."
            )
        gain = max(-6.0, min(max_boost_db, required_gain))
        if abs(gain) < 0.4:
            continue
        filters.append(
            {
                "type": "peaking",
                "frequency_hz": center_hz,
                "gain_db": round(gain, 2),
                "q": 0.7,
            }
        )

    if len(filters) > 7:
        filters = filters[:7]
    return filters


def _render_toml(
    input_path: Path,
    filters: list[dict[str, float | str]],
    profile_type: str,
    max_boost_db: float,
    safety_report: dict[str, object],
    safety_report_path: Path,
) -> str:
    now = datetime.now(UTC).isoformat()
    preamp_headroom = -max(DEFAULT_MAX_BOOST_DB, max([float(item["gain_db"]) for item in filters], default=0.0))
    lines = [
        "# PipeTune Linux measurement correction draft",
        "# WARNING: draft correction only. It is not installed, active, or applied automatically.",
        "# Built-in laptop microphones are approximate and uncalibrated.",
        "",
        "[profile]",
        'name = "PipeTune measurement correction draft"',
        f'profile_type = "{profile_type}"',
        'status = "draft"',
        f'generated_by = "PipeTune Linux v{__version__}"',
        f'generated_at = "{now}"',
        "",
        "[source]",
        f'file = "{_toml_escape(str(input_path))}"',
        'format = "normalized-frequency-response-csv"',
        'license = "unknown"',
        'method = "conservative broad-band inverse response from approximate measurement"',
        "",
        "[safety]",
        "safe_mode = true",
        f"max_boost_db = {max_boost_db:g}",
        "no_boost_below_hz = 120",
        "high_pass_required = true",
        f"preamp_headroom_db = {preamp_headroom:g}",
        'warning = "Draft only. Review, measure again, and run PipeTune safety checks before any manual use."',
        f'quality_verdict = "{safety_report["measurement_quality"]}"',
        f'safety_report_sidecar = "{_toml_escape(str(safety_report_path))}"',
        "",
        "[limiter]",
        "enabled = true",
        'mode = "metadata-only"',
        'note = "Limiter metadata is included for downstream compatibility; this draft does not apply a limiter."',
        "",
        "[[filters]]",
        'type = "high_pass"',
        "frequency_hz = 80",
        "slope_db_per_octave = 12",
        'reason = "Required conservative laptop-speaker protection high-pass."',
    ]

    for item in filters:
        lines.extend(
            [
                "",
                "[[filters]]",
                f'type = "{item["type"]}"',
                f"frequency_hz = {float(item['frequency_hz']):g}",
                f"gain_db = {float(item['gain_db']):g}",
                f"q = {float(item['q']):g}",
            ]
        )

    lines.append("")
    return "\n".join(lines)


def _safety_report(
    input_path: Path,
    filters: list[dict[str, float | str]],
    profile_type: str,
    max_boost_db: float,
    validation: dict[str, object],
) -> dict[str, object]:
    gains = [float(item["gain_db"]) for item in filters if item.get("type") == "peaking"]
    return {
        "source_file": str(input_path),
        "profile_type": profile_type,
        "status": "draft",
        "measurement_quality": validation["measurement_quality"],
        "validation": validation,
        "safety_constraints": {
            "safe_mode_required": True,
            "max_boost_db": max_boost_db,
            "no_boost_below_hz": 120,
            "high_pass_filter_mandatory": profile_type == "laptop-speaker",
            "preamp_headroom_mandatory": True,
            "limiter_metadata_mandatory": True,
            "broad_band_only": True,
        },
        "generated_filter_count": len(filters) + 1,
        "max_generated_boost_db": round(max(gains, default=0.0), 3),
        "warnings": [
            "Draft correction only; not installed, active, or applied automatically.",
            "Built-in laptop microphone measurements are approximate and uncalibrated.",
        ],
    }


def _median(values: list[float]) -> float:
    sorted_values = sorted(values)
    middle = len(sorted_values) // 2
    if len(sorted_values) % 2:
        return sorted_values[middle]
    return (sorted_values[middle - 1] + sorted_values[middle]) / 2.0


def _toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
