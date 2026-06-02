from __future__ import annotations

from pipetune.safety.models import ActivationReadiness, HardwareQuirkMetadata, ProfileSafetyCheck
from pipetune.safety.readiness import decide_activation_readiness


def _check() -> ProfileSafetyCheck:
    return ProfileSafetyCheck(
        file_path="generated/test.filter-chain.conf",
        exists=True,
        readable=True,
        appears_generated_by_pipetune=True,
        filter_chain_config=True,
        filter_count=1,
        manifest_present=True,
        preamp_metadata="present",
        safety_status="pass",
    )


def _quirk() -> HardwareQuirkMetadata:
    return HardwareQuirkMetadata(
        quirk_detected=True,
        quirk_type="manual_hda_pin_retask",
        auto_switch_safe=False,
        built_in_microphone_reliable=None,
        requires_manual_output_confirmation=True,
        evidence=["retask"],
        warnings=[],
    )


def test_hardware_quirk_metadata_model_serializes_correctly() -> None:
    assert _quirk().to_dict()["quirk_type"] == "manual_hda_pin_retask"


def test_activation_readiness_model_serializes_correctly() -> None:
    readiness = ActivationReadiness(status="ready", reasons=["ok"])

    assert readiness.to_dict()["status"] == "ready"
    assert readiness.to_dict()["reasons"] == ["ok"]


def test_readiness_requires_confirmation_for_hda_quirk() -> None:
    readiness = decide_activation_readiness(
        safety_check=_check(),
        manifest_present=True,
        profile_type="headphone",
        auto_apply_safe=False,
        requires_manual_output_confirmation=True,
        hardware_quirk=_quirk(),
    )

    assert readiness.status == "requires_confirmation"
