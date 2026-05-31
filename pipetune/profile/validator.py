"""Validation rules for parsed AudioProfile objects."""

from __future__ import annotations

import math

from pipetune.profile.models import AudioProfile, AutoEqParseResult, EqFilter, ProfileValidationResult

_SUPPORTED_FILTER_TYPES = {"PK", "LS", "HS"}


def _validate_filter(filter_item: EqFilter, errors: list[str], warnings: list[str]) -> None:
    if not filter_item.enabled:
        return

    if filter_item.filter_type not in _SUPPORTED_FILTER_TYPES:
        errors.append(
            f"Filter {filter_item.index}: unsupported enabled filter type '{filter_item.filter_type}'."
        )

    if not math.isfinite(filter_item.frequency_hz):
        errors.append(f"Filter {filter_item.index}: invalid numeric value for frequency.")
    elif filter_item.frequency_hz < 10:
        warnings.append(f"Filter {filter_item.index}: frequency below 10 Hz ({filter_item.frequency_hz:g} Hz).")
    elif filter_item.frequency_hz > 24000:
        warnings.append(f"Filter {filter_item.index}: frequency above 24000 Hz ({filter_item.frequency_hz:g} Hz).")

    if not math.isfinite(filter_item.gain_db):
        errors.append(f"Filter {filter_item.index}: invalid numeric value for gain.")
    elif filter_item.gain_db > 6:
        warnings.append(f"Filter {filter_item.index}: gain boost above +6 dB ({filter_item.gain_db:g} dB).")

    if not math.isfinite(filter_item.q):
        errors.append(f"Filter {filter_item.index}: invalid numeric value for Q.")
    elif filter_item.q < 0.1:
        warnings.append(f"Filter {filter_item.index}: Q lower than 0.1 ({filter_item.q:g}).")
    elif filter_item.q > 20:
        warnings.append(f"Filter {filter_item.index}: Q higher than 20 ({filter_item.q:g}).")


def validate_profile(parse_result: AutoEqParseResult | AudioProfile) -> ProfileValidationResult:
    if isinstance(parse_result, AudioProfile):
        profile = parse_result
        errors: list[str] = []
    else:
        profile = parse_result.profile
        errors = list(parse_result.errors)

    warnings = list(profile.warnings)

    if profile.preamp_db is None:
        warnings.append("Missing preamp value.")
    elif profile.preamp_db > 0:
        warnings.append(f"Preamp is higher than 0 dB ({profile.preamp_db:g} dB).")

    if not profile.filters:
        errors.append("No filters found.")

    if len(profile.filters) > 20:
        warnings.append(f"Profile has more than 20 filters ({len(profile.filters)}).")

    for filter_item in profile.filters:
        _validate_filter(filter_item, errors, warnings)

    return ProfileValidationResult(valid=not errors, errors=errors, warnings=warnings)
