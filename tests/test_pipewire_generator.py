from __future__ import annotations

from pathlib import Path

import pytest

from pipetune.profile.models import AudioProfile, EqFilter
from pipetune.profile.pipewire_generator import (
    generate_pipewire_filter_chain_config,
    sanitize_profile_name,
    write_generated_config,
)


def _profile_with_types() -> AudioProfile:
    return AudioProfile(
        name="Test Profile",
        preamp_db=-3.0,
        source_format="autoeq",
        warnings=[],
        filters=[
            EqFilter(index=1, enabled=True, filter_type="PK", frequency_hz=100.0, gain_db=-1.0, q=1.0),
            EqFilter(index=2, enabled=True, filter_type="LS", frequency_hz=200.0, gain_db=2.0, q=0.7),
            EqFilter(index=3, enabled=True, filter_type="HS", frequency_hz=5000.0, gain_db=-2.0, q=1.2),
        ],
    )


def test_generated_config_contains_profile_name() -> None:
    config = generate_pipewire_filter_chain_config(_profile_with_types(), Path("sample.txt"))
    assert "Profile: Test Profile" in config


def test_generated_config_contains_bq_peaking_for_pk_filters() -> None:
    config = generate_pipewire_filter_chain_config(_profile_with_types(), Path("sample.txt"))
    assert "label = bq_peaking" in config


def test_generated_config_contains_bq_lowshelf_for_ls_filters() -> None:
    config = generate_pipewire_filter_chain_config(_profile_with_types(), Path("sample.txt"))
    assert "label = bq_lowshelf" in config


def test_generated_config_contains_bq_highshelf_for_hs_filters() -> None:
    config = generate_pipewire_filter_chain_config(_profile_with_types(), Path("sample.txt"))
    assert "label = bq_highshelf" in config


def test_generated_config_does_not_include_disabled_filters() -> None:
    profile = AudioProfile(
        name="Disabled Filter Test",
        preamp_db=-1.0,
        source_format="autoeq",
        warnings=[],
        filters=[
            EqFilter(index=1, enabled=True, filter_type="PK", frequency_hz=100.0, gain_db=1.0, q=1.0),
            EqFilter(index=2, enabled=False, filter_type="PK", frequency_hz=300.0, gain_db=2.0, q=1.0),
        ],
    )

    config = generate_pipewire_filter_chain_config(profile, Path("sample.txt"))
    assert "name = eq_1" in config
    assert "name = eq_2" not in config


def test_output_filename_is_sanitized() -> None:
    assert sanitize_profile_name("Sennheiser HD 650") == "sennheiser-hd-650.filter-chain.conf"
    assert sanitize_profile_name("sony wh-1000xm5") == "sony-wh-1000xm5.filter-chain.conf"


def test_generation_refuses_invalid_profile() -> None:
    invalid_profile = AudioProfile(name="invalid", preamp_db=None, source_format="autoeq", warnings=[], filters=[])

    with pytest.raises(ValueError):
        generate_pipewire_filter_chain_config(invalid_profile, Path("sample.txt"))


def test_write_generated_config_writes_to_sanitized_path(tmp_path: Path) -> None:
    profile = _profile_with_types()
    profile.name = "Sennheiser HD 650"

    output_path = write_generated_config(profile, Path("input.txt"), tmp_path)

    assert output_path.name == "sennheiser-hd-650.filter-chain.conf"
    assert output_path.exists()
