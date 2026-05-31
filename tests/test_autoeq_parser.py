from __future__ import annotations

from pipetune.profile.autoeq_parser import parse_autoeq_text


def test_parses_preamp_correctly() -> None:
    text = "Preamp: -6.8 dB\nFilter 1: ON PK Fc 20 Hz Gain -1.0 dB Q 1.0\n"
    result = parse_autoeq_text(text, source_name="sample.txt")

    assert result.profile.preamp_db == -6.8
    assert not result.errors


def test_parses_enabled_pk_filters_correctly() -> None:
    text = "Filter 1: ON PK Fc 20 Hz Gain -1.3 dB Q 2.000\nFilter 2: ON Peaking Fc 50 Hz Gain 1.0 dB Q 0.7\n"
    result = parse_autoeq_text(text)

    assert len(result.profile.filters) == 2
    assert result.profile.filters[0].filter_type == "PK"
    assert result.profile.filters[1].filter_type == "PK"


def test_ignores_off_filters() -> None:
    text = "Filter 1: OFF PK Fc 20 Hz Gain -1.3 dB Q 2.000\nFilter 2: ON PK Fc 50 Hz Gain 1.0 dB Q 0.7\n"
    result = parse_autoeq_text(text)

    assert len(result.profile.filters) == 1
    assert result.profile.filters[0].index == 2


def test_handles_comments_and_empty_lines() -> None:
    text = "\n# comment\n// another comment\nPreamp: -2 dB\n\nFilter 1: ON PK Fc 80 Hz Gain -1 dB Q 1.2\n"
    result = parse_autoeq_text(text)

    assert result.profile.preamp_db == -2.0
    assert len(result.profile.filters) == 1
    assert not result.errors


def test_handles_irregular_spacing() -> None:
    text = "  Preamp :   -3.5 dB\nFilter   1:   ON   PK   Fc   100   Hz   Gain   2.0 dB   Q  0.9\n"
    result = parse_autoeq_text(text)

    assert result.profile.preamp_db == -3.5
    assert len(result.profile.filters) == 1
    assert result.profile.filters[0].frequency_hz == 100.0


def test_reports_malformed_lines() -> None:
    text = "Filter 1 ON PK Fc 100 Hz Gain 2.0 dB Q 1.0\n"
    result = parse_autoeq_text(text)

    assert result.errors
    assert any("malformed filter line" in error.lower() for error in result.errors)
