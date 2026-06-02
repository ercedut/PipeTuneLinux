"""Frequency response comparison helpers."""

from __future__ import annotations

import json
from pathlib import Path

from pipetune.measurement import MeasurementError
from pipetune.measurement.response import read_normalized_response_csv, validate_response_csv

MIN_SHARED_GRID_POINTS = 3
BANDS = {
    "sub_bass": (20.0, 60.0),
    "bass": (60.0, 250.0),
    "low_mid": (250.0, 500.0),
    "mid": (500.0, 2000.0),
    "upper_mid": (2000.0, 4000.0),
    "treble": (4000.0, 10000.0),
    "air": (10000.0, 20000.0),
}

def compare_responses(before_path: Path, after_path: Path, output_path: Path) -> dict[str, object]:
    before_validation = validate_response_csv(before_path)
    after_validation = validate_response_csv(after_path)
    if before_validation.errors:
        raise MeasurementError(f"Before response validation failed: {before_validation.errors[0]}")
    if after_validation.errors:
        raise MeasurementError(f"After response validation failed: {after_validation.errors[0]}")

    before = read_normalized_response_csv(before_path)
    after = read_normalized_response_csv(after_path)
    grid = _shared_grid(before, after)
    if len(grid) < MIN_SHARED_GRID_POINTS:
        raise MeasurementError("Response files do not have an overlapping frequency range.")

    before_values = [_interpolate(before, frequency) for frequency in grid]
    after_values = [_interpolate(after, frequency) for frequency in grid]
    diffs = [after_value - before_value for before_value, after_value in zip(before_values, after_values)]
    abs_diffs = [abs(value) for value in diffs]

    report: dict[str, object] = {
        "before_file": str(before_path),
        "after_file": str(after_path),
        "grid_point_count": len(grid),
        "min_freq_hz": round(min(grid), 3),
        "max_freq_hz": round(max(grid), 3),
        "frequency_overlap_warning": _overlap_warning(grid),
        "average_absolute_difference_db": round(sum(abs_diffs) / len(abs_diffs), 3),
        "max_absolute_difference_db": round(max(abs_diffs), 3),
        "band_summaries": {
            name: _band_summary(grid, diffs, low, high)
            for name, (low, high) in BANDS.items()
        },
        "variance_before": round(_variance(before_values), 3),
        "variance_after": round(_variance(after_values), 3),
        "before_variance_db2": round(_variance(before_values), 3),
        "after_variance_db2": round(_variance(after_values), 3),
        "flatter_by_variance": _variance(after_values) < _variance(before_values),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def _shared_grid(before: list[tuple[float, float]], after: list[tuple[float, float]]) -> list[float]:
    low = max(before[0][0], after[0][0])
    high = min(before[-1][0], after[-1][0])
    frequencies = sorted(
        {
            frequency
            for frequency, _magnitude in before + after
            if low <= frequency <= high
        }
    )
    return frequencies


def _interpolate(rows: list[tuple[float, float]], frequency: float) -> float:
    if frequency <= rows[0][0]:
        return rows[0][1]
    if frequency >= rows[-1][0]:
        return rows[-1][1]
    for left, right in zip(rows, rows[1:]):
        left_freq, left_mag = left
        right_freq, right_mag = right
        if left_freq <= frequency <= right_freq:
            if right_freq == left_freq:
                return left_mag
            fraction = (frequency - left_freq) / (right_freq - left_freq)
            return left_mag + fraction * (right_mag - left_mag)
    return rows[-1][1]


def _band_summary(grid: list[float], diffs: list[float], low: float, high: float) -> dict[str, float | int | None]:
    values = [diff for frequency, diff in zip(grid, diffs) if low <= frequency < high]
    if not values:
        return {"point_count": 0, "average_difference_db": None, "average_absolute_difference_db": None}
    return {
        "point_count": len(values),
        "average_difference_db": round(sum(values) / len(values), 3),
        "average_absolute_difference_db": round(sum(abs(value) for value in values) / len(values), 3),
    }


def _variance(values: list[float]) -> float:
    mean = sum(values) / len(values)
    return sum((value - mean) ** 2 for value in values) / len(values)


def _overlap_warning(grid: list[float]) -> str | None:
    if len(grid) < 6 or (max(grid) / min(grid) if min(grid) > 0 else 0) < 10:
        return "Warning: frequency overlap is small; comparison is approximate."
    return None
