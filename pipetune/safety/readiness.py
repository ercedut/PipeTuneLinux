"""Activation readiness decision engine."""

from __future__ import annotations

from pipetune.safety.models import ActivationReadiness, HardwareQuirkMetadata, ProfileSafetyCheck


def decide_activation_readiness(
    *,
    safety_check: ProfileSafetyCheck,
    manifest_present: bool,
    profile_type: str,
    auto_apply_safe: bool,
    requires_manual_output_confirmation: bool,
    hardware_quirk: HardwareQuirkMetadata,
) -> ActivationReadiness:
    reasons: list[str] = []
    warnings: list[str] = list(safety_check.warnings)
    next_steps = [
        "Run profile safety-check.",
        "Use profile install only with --user --confirm-install.",
    ]

    if safety_check.errors:
        reasons.extend(safety_check.errors)
        return ActivationReadiness(
            status="blocked",
            reasons=reasons,
            warnings=warnings,
            recommended_next_steps=["Fix the reported config errors before activation."],
        )

    if safety_check.safety_status == "fail":
        reasons.append("Profile safety check failed.")
        return ActivationReadiness(
            status="blocked",
            reasons=reasons,
            warnings=warnings,
            recommended_next_steps=["Fix safety-check errors before activation."],
        )

    if not manifest_present:
        return ActivationReadiness(
            status="unknown",
            reasons=["Manifest is missing."],
            warnings=warnings,
            recommended_next_steps=["Create a profile manifest before activation preflight."],
        )

    if profile_type == "unknown":
        reasons.append("Profile type is unknown.")
        return ActivationReadiness(
            status="blocked",
            reasons=reasons,
            warnings=warnings,
            recommended_next_steps=["Create a manifest with an explicit profile type."],
        )

    if profile_type == "laptop_speaker" and not manifest_present:
        reasons.append("Laptop speaker profile is missing required safety metadata.")
        return ActivationReadiness(
            status="blocked",
            reasons=reasons,
            warnings=warnings,
            recommended_next_steps=["Create and review a manifest before any activation flow."],
        )

    if hardware_quirk.quirk_detected and not requires_manual_output_confirmation:
        reasons.append("Hardware quirk detected and profile has no manual confirmation path.")
        return ActivationReadiness(
            status="blocked",
            reasons=reasons,
            warnings=warnings,
            recommended_next_steps=["Regenerate manifest with manual output confirmation required."],
        )

    if hardware_quirk.quirk_detected or requires_manual_output_confirmation or not auto_apply_safe:
        reasons.append("Hardware quirk detected on this machine." if hardware_quirk.quirk_detected else "Manual output confirmation is required.")
        if hardware_quirk.quirk_detected:
            reasons.append("Headphone/speaker routing may not match logical PipeWire route.")
        return ActivationReadiness(
            status="requires_confirmation",
            reasons=reasons,
            warnings=warnings,
            recommended_next_steps=["Confirm the physical output target manually.", *next_steps],
        )

    return ActivationReadiness(
        status="ready",
        reasons=["Manifest present, generated config detected, and no hardware quirk conflict found."],
        warnings=warnings,
        recommended_next_steps=next_steps,
    )
