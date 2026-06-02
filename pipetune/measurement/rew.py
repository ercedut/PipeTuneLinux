"""REW-style CSV import helpers."""

from __future__ import annotations

import csv
import json
import math
from datetime import UTC, datetime
from pathlib import Path

from pipetune.measurement import MeasurementError

FREQUENCY_COLUMNS = {"frequency", "freq", "hz", "freq_hz"}
MAGNITUDE_COLUMNS = {"spl", "magnitude", "db", "magnitude_db"}
MAX_SKIPPED_ROW_RATIO = 0.5


def import_rew_csv(input_path: Path, output_path: Path) -> dict[str, object]:
    rows, details = _read_rew_rows(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["freq_hz", "magnitude_db"])
        for frequency, magnitude in rows:
            writer.writerow([f"{frequency:.6g}", f"{magnitude:.6g}"])

    frequencies = [frequency for frequency, _magnitude in rows]
    metadata: dict[str, object] = {
        "source_format": "REW",
        "row_count": len(rows),
        "skipped_row_count": details["skipped_row_count"],
        "detected_frequency_column": details["detected_frequency_column"],
        "detected_magnitude_column": details["detected_magnitude_column"],
        "min_freq_hz": min(frequencies),
        "max_freq_hz": max(frequencies),
        "imported_at": datetime.now(UTC).isoformat(),
        "warnings": details["warnings"],
    }
    output_path.with_suffix(output_path.suffix + ".json").write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )
    return metadata


def _read_rew_rows(input_path: Path) -> tuple[list[tuple[float, float]], dict[str, object]]:
    if not input_path.exists():
        raise MeasurementError(f"REW CSV does not exist: {input_path}")

    with input_path.open("r", encoding="utf-8-sig", newline="") as input_file:
        reader = csv.DictReader(input_file)
        if not reader.fieldnames:
            raise MeasurementError("Malformed REW CSV: missing header row.")
        frequency_column = _find_column(reader.fieldnames, FREQUENCY_COLUMNS)
        magnitude_column = _find_column(reader.fieldnames, MAGNITUDE_COLUMNS)
        if frequency_column is None or magnitude_column is None:
            raise MeasurementError("Malformed REW CSV: expected frequency and magnitude columns.")

        rows: list[tuple[float, float]] = []
        skipped_row_count = 0
        total_rows = 0
        warnings: list[str] = []
        for line_number, row in enumerate(reader, start=2):
            total_rows += 1
            raw_frequency = str(row.get(frequency_column, "")).strip()
            raw_magnitude = str(row.get(magnitude_column, "")).strip()
            if not raw_frequency and not raw_magnitude:
                skipped_row_count += 1
                continue
            if not raw_frequency or not raw_magnitude:
                skipped_row_count += 1
                continue
            try:
                frequency = _parse_decimal(raw_frequency)
            except ValueError as exc:
                raise MeasurementError(f"Malformed REW CSV: invalid frequency value on line {line_number}.") from exc
            try:
                magnitude = _parse_decimal(raw_magnitude)
            except ValueError as exc:
                raise MeasurementError(f"Malformed REW CSV: invalid magnitude value on line {line_number}.") from exc
            if not math.isfinite(frequency) or frequency <= 0:
                raise MeasurementError(f"Malformed REW CSV: frequency must be positive on line {line_number}.")
            if not math.isfinite(magnitude):
                raise MeasurementError(f"Malformed REW CSV: magnitude must be finite on line {line_number}.")
            rows.append((frequency, magnitude))

    if not rows:
        raise MeasurementError("Malformed REW CSV: no measurement rows found.")
    if total_rows and skipped_row_count / total_rows > MAX_SKIPPED_ROW_RATIO:
        raise MeasurementError(
            f"Malformed REW CSV: too many malformed rows were skipped ({skipped_row_count}/{total_rows})."
        )
    if skipped_row_count:
        warnings.append(f"Skipped malformed or incomplete rows: {skipped_row_count}.")
    return rows, {
        "skipped_row_count": skipped_row_count,
        "detected_frequency_column": frequency_column,
        "detected_magnitude_column": magnitude_column,
        "warnings": warnings,
    }


def _find_column(fieldnames: list[str], accepted: set[str]) -> str | None:
    for fieldname in fieldnames:
        normalized = fieldname.strip().lower().replace(" ", "_")
        if normalized in accepted:
            return fieldname
    return None


def _parse_decimal(value: str) -> float:
    text = value.strip()
    if "," in text and "." not in text:
        text = text.replace(",", ".")
    return float(text)
