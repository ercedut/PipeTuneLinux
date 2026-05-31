from __future__ import annotations

from pathlib import Path

from pipetune.profile.autoeq_parser import parse_autoeq_file, parse_autoeq_text
from pipetune.profile.models import AudioProfile, EqFilter
from pipetune.profile.validator import validate_profile


def test_no_filters_is_error() -> None:
    profile = AudioProfile(name="empty", preamp_db=-1.0, filters=[], source_format="autoeq", warnings=[])
    result = validate_profile(profile)

    assert result.valid is False
    assert any("no filters found" in error.lower() for error in result.errors)


def test_missing_preamp_is_warning() -> None:
    text = "Filter 1: ON PK Fc 100 Hz Gain -1.0 dB Q 1.0\n"
    parsed = parse_autoeq_text(text)
    result = validate_profile(parsed)

    assert result.valid is True
    assert any("missing preamp" in warning.lower() for warning in result.warnings)


def test_gain_above_plus_6_db_is_warning() -> None:
    text = "Preamp: -2 dB\nFilter 1: ON PK Fc 100 Hz Gain 7.0 dB Q 1.0\n"
    parsed = parse_autoeq_text(text)
    result = validate_profile(parsed)

    assert result.valid is True
    assert any("above +6 db" in warning.lower() for warning in result.warnings)


def test_unsupported_enabled_filter_type_is_error() -> None:
    profile = AudioProfile(
        name="unsupported",
        preamp_db=-2.0,
        filters=[EqFilter(index=1, enabled=True, filter_type="NOTCH", frequency_hz=100.0, gain_db=1.0, q=1.0)],
        source_format="autoeq",
        warnings=[],
    )

    result = validate_profile(profile)

    assert result.valid is False
    assert any("unsupported enabled filter type" in error.lower() for error in result.errors)


def test_valid_sample_passes() -> None:
    parsed = parse_autoeq_file(Path("examples/autoeq/sennheiser-hd650.txt"))
    result = validate_profile(parsed)

    assert result.valid is True
    assert not result.errors
