"""AutoEQ parametric EQ parser."""

from __future__ import annotations

import re
from pathlib import Path

from pipetune.profile.models import AudioProfile, AutoEqParseResult, EqFilter

_PREAMP_RE = re.compile(r"^\s*preamp\s*:\s*([+-]?\d+(?:\.\d+)?)\s*dB\s*$", re.IGNORECASE)
_FILTER_RE = re.compile(r"^\s*filter\s+(\d+)\s*:\s*(on|off)\s+([a-zA-Z_]+)\s*(.*)$", re.IGNORECASE)
_NUMBER_RE = r"([+-]?\d+(?:\.\d+)?)"
_FC_RE = re.compile(rf"\bfc\b\s*{_NUMBER_RE}\s*hz\b", re.IGNORECASE)
_GAIN_RE = re.compile(rf"\bgain\b\s*{_NUMBER_RE}\s*dB\b", re.IGNORECASE)
_Q_RE = re.compile(rf"\bq\b\s*{_NUMBER_RE}\b", re.IGNORECASE)


def _normalize_filter_type(raw_filter_type: str) -> str:
    normalized = raw_filter_type.strip().replace("-", "_").upper()

    if normalized in {"PK", "PEAK", "PEAKING"}:
        return "PK"
    if normalized in {"LS", "LOW_SHELF", "LOWSHELF"}:
        return "LS"
    if normalized in {"HS", "HIGH_SHELF", "HIGHSHELF"}:
        return "HS"
    return normalized


def _line_is_comment_or_empty(line: str) -> bool:
    stripped = line.strip()
    return not stripped or stripped.startswith("#") or stripped.startswith("//")


def _parse_numeric_field(
    text: str,
    regex: re.Pattern[str],
    field_label: str,
    filter_index: int,
    errors: list[str],
) -> float | None:
    match = regex.search(text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            errors.append(f"Filter {filter_index}: invalid numeric value for {field_label}.")
            return None

    if re.search(rf"\b{re.escape(field_label)}\b", text, re.IGNORECASE):
        errors.append(f"Filter {filter_index}: invalid numeric value for {field_label}.")
    else:
        errors.append(f"Filter {filter_index}: missing {field_label} value.")
    return None


def parse_autoeq_text(text: str, source_name: str = "autoeq-input") -> AutoEqParseResult:
    errors: list[str] = []
    warnings: list[str] = []
    filters: list[EqFilter] = []
    preamp_db: float | None = None

    for line_number, line in enumerate(text.splitlines(), start=1):
        if _line_is_comment_or_empty(line):
            continue

        preamp_match = _PREAMP_RE.match(line)
        if preamp_match:
            try:
                preamp_db = float(preamp_match.group(1))
            except ValueError:
                errors.append(f"Line {line_number}: invalid numeric preamp value.")
            continue

        filter_match = _FILTER_RE.match(line)
        if filter_match:
            filter_index = int(filter_match.group(1))
            enabled = filter_match.group(2).strip().upper() == "ON"
            filter_type = _normalize_filter_type(filter_match.group(3))
            remainder = filter_match.group(4)

            frequency_hz = _parse_numeric_field(remainder, _FC_RE, "Fc", filter_index, errors)
            gain_db = _parse_numeric_field(remainder, _GAIN_RE, "Gain", filter_index, errors)
            q_value = _parse_numeric_field(remainder, _Q_RE, "Q", filter_index, errors)

            if enabled and frequency_hz is not None and gain_db is not None and q_value is not None:
                filters.append(
                    EqFilter(
                        index=filter_index,
                        enabled=True,
                        filter_type=filter_type,
                        frequency_hz=frequency_hz,
                        gain_db=gain_db,
                        q=q_value,
                    )
                )
            continue

        if line.strip().lower().startswith("filter"):
            errors.append(f"Line {line_number}: malformed filter line.")
            continue

        warnings.append(f"Line {line_number}: ignored unrecognized content.")

    profile_name = Path(source_name).stem
    profile = AudioProfile(
        name=profile_name,
        preamp_db=preamp_db,
        filters=sorted(filters, key=lambda item: item.index),
        source_format="autoeq-parametric-eq",
        warnings=warnings,
    )
    return AutoEqParseResult(profile=profile, errors=errors)


def parse_autoeq_file(path: Path) -> AutoEqParseResult:
    return parse_autoeq_text(path.read_text(encoding="utf-8"), source_name=str(path))
