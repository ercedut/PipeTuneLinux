"""Normalized frequency response loading and validation."""

from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

from pipetune.measurement import MeasurementError

MIN_RESPONSE_POINTS = 5
MIN_CORRECTION_POINTS = 6
MIN_COVERAGE_RATIO = 20.0
UNREALISTIC_MAGNITUDE_DB = 60.0
WARNING_MAGNITUDE_DB = 40.0
UNREALISTIC_JUMP_DB = 30.0
WARNING_JUMP_DB = 12.0


@dataclass(slots=True)
class ResponseValidationReport:
    input_file: str
    row_count: int
    min_freq_hz: float | None
    max_freq_hz: float | None
    sorted_frequency_data: bool
    duplicate_frequency_count: int
    unrealistic_magnitude_count: int
    max_adjacent_magnitude_jump_db: float | None
    quality_flags: list[str]
    warnings: list[str]
    errors: list[str]
    measurement_quality: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def read_normalized_response_csv(path: Path) -> list[tuple[float, float]]:
    rows, errors = _parse_normalized_response_csv(path)
    if errors:
        raise MeasurementError(errors[0])
    if not rows:
        raise MeasurementError("Response CSV contains no measurement rows.")
    return sorted(rows)


def validate_response_csv(path: Path) -> ResponseValidationReport:
    rows, parse_errors = _parse_normalized_response_csv(path)
    errors = list(parse_errors)
    warnings: list[str] = []
    flags: list[str] = []

    row_count = len(rows)
    sorted_frequency_data = True
    duplicate_frequency_count = 0
    unrealistic_magnitude_count = 0
    max_jump: float | None = None

    if row_count < MIN_RESPONSE_POINTS:
        errors.append(f"Too few response points: {row_count}; at least {MIN_RESPONSE_POINTS} are required.")
        flags.append("too_few_points")

    if rows:
        frequencies = [frequency for frequency, _magnitude in rows]
        magnitudes = [magnitude for _frequency, magnitude in rows]
        sorted_frequency_data = frequencies == sorted(frequencies)
        if not sorted_frequency_data:
            warnings.append("Warning: frequency rows are unsorted; PipeTune will sort them for analysis.")
            flags.append("unsorted")

        seen: set[float] = set()
        for frequency in frequencies:
            if frequency in seen:
                duplicate_frequency_count += 1
            seen.add(frequency)
        if duplicate_frequency_count:
            errors.append(f"Duplicate frequency rows detected: {duplicate_frequency_count}.")
            flags.append("duplicate_frequencies")

        unrealistic_magnitude_count = sum(1 for magnitude in magnitudes if abs(magnitude) > UNREALISTIC_MAGNITUDE_DB)
        if unrealistic_magnitude_count:
            errors.append(f"Unrealistic magnitude values detected: {unrealistic_magnitude_count}.")
            flags.append("unrealistic_magnitude")
        elif any(abs(magnitude) > WARNING_MAGNITUDE_DB for magnitude in magnitudes):
            warnings.append("Warning: large magnitude values detected; measurement is approximate.")
            flags.append("large_magnitude")

        sorted_rows = sorted(rows)
        jumps = [abs(right[1] - left[1]) for left, right in zip(sorted_rows, sorted_rows[1:])]
        if jumps:
            max_jump = max(jumps)
            if max_jump > UNREALISTIC_JUMP_DB:
                errors.append(f"Unrealistic adjacent magnitude jump detected: {max_jump:.2f} dB.")
                flags.append("unrealistic_magnitude_jump")
            elif max_jump > WARNING_JUMP_DB:
                warnings.append(f"Warning: large adjacent magnitude jump detected: {max_jump:.2f} dB.")
                flags.append("large_magnitude_jump")

        min_freq = min(frequencies)
        max_freq = max(frequencies)
        coverage_ratio = max_freq / min_freq if min_freq > 0 else 0.0
        if coverage_ratio < MIN_COVERAGE_RATIO:
            errors.append(
                f"Frequency coverage is too narrow: {min_freq:g}-{max_freq:g} Hz."
            )
            flags.append("narrow_coverage")
        elif min_freq > 40 or max_freq < 16000:
            warnings.append(
                f"Warning: limited frequency coverage: {min_freq:g}-{max_freq:g} Hz."
            )
            flags.append("limited_coverage")
    else:
        min_freq = None
        max_freq = None

    if errors:
        quality = "fail"
    elif warnings:
        quality = "warn"
    else:
        quality = "pass"
        warnings.append("Pass: normalized response data is usable for approximate analysis.")
    warnings.append("Built-in laptop microphones remain approximate and uncalibrated.")

    return ResponseValidationReport(
        input_file=str(path),
        row_count=row_count,
        min_freq_hz=round(min_freq, 6) if min_freq is not None else None,
        max_freq_hz=round(max_freq, 6) if max_freq is not None else None,
        sorted_frequency_data=sorted_frequency_data,
        duplicate_frequency_count=duplicate_frequency_count,
        unrealistic_magnitude_count=unrealistic_magnitude_count,
        max_adjacent_magnitude_jump_db=round(max_jump, 3) if max_jump is not None else None,
        quality_flags=flags,
        warnings=warnings,
        errors=errors,
        measurement_quality=quality,
    )


def render_response_validation(report: ResponseValidationReport, *, json_output: bool = False) -> str:
    if json_output:
        return json.dumps(report.to_dict(), indent=2)

    lines = [
        "PipeTune Response Validation",
        f"- Input: {report.input_file}",
        f"- Rows: {report.row_count}",
        f"- Frequency range: {_range_label(report.min_freq_hz, report.max_freq_hz)}",
        f"- Sorted frequency data: {'yes' if report.sorted_frequency_data else 'no'}",
        f"- Duplicate frequencies: {report.duplicate_frequency_count}",
        f"- Unrealistic magnitude values: {report.unrealistic_magnitude_count}",
        f"- Max adjacent magnitude jump: {_jump_label(report.max_adjacent_magnitude_jump_db)}",
        f"- Verdict: {report.measurement_quality}",
    ]
    if report.errors:
        lines.extend(["", "Errors:"])
        lines.extend(f"- {error}" for error in report.errors)
    if report.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {warning}" for warning in report.warnings)
    lines.append("")
    lines.append("No system configuration was modified.")
    return "\n".join(lines)


def _parse_normalized_response_csv(path: Path) -> tuple[list[tuple[float, float]], list[str]]:
    if not path.exists():
        return [], [f"Response CSV does not exist: {path}"]
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as input_file:
            reader = csv.DictReader(input_file)
            if not reader.fieldnames or "freq_hz" not in reader.fieldnames or "magnitude_db" not in reader.fieldnames:
                return [], ["Response CSV must contain freq_hz and magnitude_db columns."]
            rows: list[tuple[float, float]] = []
            errors: list[str] = []
            for line_number, row in enumerate(reader, start=2):
                try:
                    frequency = _parse_float(row.get("freq_hz", ""))
                    magnitude = _parse_float(row.get("magnitude_db", ""))
                except ValueError:
                    errors.append(f"Response CSV has invalid numeric value on line {line_number}.")
                    continue
                if not math.isfinite(frequency) or frequency <= 0:
                    errors.append(f"Response CSV frequency must be positive on line {line_number}.")
                    continue
                if not math.isfinite(magnitude):
                    errors.append(f"Response CSV magnitude must be finite on line {line_number}.")
                    continue
                rows.append((frequency, magnitude))
            return rows, errors
    except OSError as exc:
        return [], [f"Unable to read response CSV: {exc}"]


def _parse_float(value: object) -> float:
    text = str(value).strip()
    if "," in text and "." not in text:
        text = text.replace(",", ".")
    return float(text)


def _range_label(min_freq: float | None, max_freq: float | None) -> str:
    if min_freq is None or max_freq is None:
        return "not available"
    return f"{min_freq:g}-{max_freq:g} Hz"


def _jump_label(value: float | None) -> str:
    if value is None:
        return "not available"
    return f"{value:g} dB"
