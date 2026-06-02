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


def import_rew_csv(input_path: Path, output_path: Path) -> dict[str, object]:
    rows = _read_rew_rows(input_path)
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
        "min_freq_hz": min(frequencies),
        "max_freq_hz": max(frequencies),
        "imported_at": datetime.now(UTC).isoformat(),
        "warnings": [],
    }
    output_path.with_suffix(output_path.suffix + ".json").write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )
    return metadata


def _read_rew_rows(input_path: Path) -> list[tuple[float, float]]:
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
        for line_number, row in enumerate(reader, start=2):
            try:
                frequency = float(str(row.get(frequency_column, "")).strip())
                magnitude = float(str(row.get(magnitude_column, "")).strip())
            except ValueError as exc:
                raise MeasurementError(f"Malformed REW CSV: invalid numeric value on line {line_number}.") from exc
            if not math.isfinite(frequency) or frequency <= 0:
                raise MeasurementError(f"Malformed REW CSV: frequency must be positive on line {line_number}.")
            if not math.isfinite(magnitude):
                raise MeasurementError(f"Malformed REW CSV: magnitude must be finite on line {line_number}.")
            rows.append((frequency, magnitude))

    if not rows:
        raise MeasurementError("Malformed REW CSV: no measurement rows found.")
    return rows


def _find_column(fieldnames: list[str], accepted: set[str]) -> str | None:
    for fieldname in fieldnames:
        normalized = fieldname.strip().lower().replace(" ", "_")
        if normalized in accepted:
            return fieldname
    return None

