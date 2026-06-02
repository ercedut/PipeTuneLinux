"""Frequency response comparison helpers."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

from pipetune.measurement import MeasurementError


def compare_responses(before_path: Path, after_path: Path, output_path: Path) -> dict[str, object]:
    before = read_normalized_response_csv(before_path)
    after = read_normalized_response_csv(after_path)
    grid = _shared_grid(before, after)
    if not grid:
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
        "average_absolute_difference_db": round(sum(abs_diffs) / len(abs_diffs), 3),
        "max_absolute_difference_db": round(max(abs_diffs), 3),
        "band_summaries": {
            "low": _band_summary(grid, diffs, 20.0, 250.0),
            "mid": _band_summary(grid, diffs, 250.0, 4000.0),
            "high": _band_summary(grid, diffs, 4000.0, 20000.0),
        },
        "before_variance_db2": round(_variance(before_values), 3),
        "after_variance_db2": round(_variance(after_values), 3),
        "flatter_by_variance": _variance(after_values) < _variance(before_values),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def read_normalized_response_csv(path: Path) -> list[tuple[float, float]]:
    if not path.exists():
        raise MeasurementError(f"Response CSV does not exist: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as input_file:
        reader = csv.DictReader(input_file)
        if not reader.fieldnames or "freq_hz" not in reader.fieldnames or "magnitude_db" not in reader.fieldnames:
            raise MeasurementError("Response CSV must contain freq_hz and magnitude_db columns.")
        rows: list[tuple[float, float]] = []
        for line_number, row in enumerate(reader, start=2):
            try:
                frequency = float(str(row["freq_hz"]).strip())
                magnitude = float(str(row["magnitude_db"]).strip())
            except ValueError as exc:
                raise MeasurementError(f"Response CSV has invalid numeric value on line {line_number}.") from exc
            if not math.isfinite(frequency) or frequency <= 0:
                raise MeasurementError(f"Response CSV frequency must be positive on line {line_number}.")
            if not math.isfinite(magnitude):
                raise MeasurementError(f"Response CSV magnitude must be finite on line {line_number}.")
            rows.append((frequency, magnitude))

    if not rows:
        raise MeasurementError("Response CSV contains no measurement rows.")
    return sorted(rows)


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

