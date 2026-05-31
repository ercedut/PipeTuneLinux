"""Guided manual HDA repair planning."""

from __future__ import annotations

from pathlib import Path

from pipetune.repair.models import RepairContext

DEFAULT_AUDIT_DIR = Path("docs/system-audits/erce-hda-pin-retask")


def _read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _detect_bool_from_text(text: str, true_tokens: tuple[str, ...], false_tokens: tuple[str, ...]) -> bool | None:
    lowered = text.lower()
    if any(token in lowered for token in true_tokens):
        return True
    if any(token in lowered for token in false_tokens):
        return False
    return None


def build_repair_context(audit_dir: Path = DEFAULT_AUDIT_DIR) -> RepairContext:
    raw_dir = audit_dir / "raw"
    readme_text = _read_text_if_exists(audit_dir / "README.md")
    public_summary_text = _read_text_if_exists(audit_dir / "PUBLIC_SUMMARY.md")
    hda_search_text = _read_text_if_exists(raw_dir / "hda-retask-search.txt")

    speaker_output_working = _detect_bool_from_text(
        f"{readme_text}\n{public_summary_text}",
        true_tokens=("speaker output currently works", "speaker output currently works and must not be broken"),
        false_tokens=("speaker output regresses",),
    )

    hda_retask_detected = _detect_bool_from_text(
        f"{hda_search_text}\n{public_summary_text}\n{readme_text}",
        true_tokens=("hda-jack-retask", "manual hda retask status: detected", "hardware quirk status: detected"),
        false_tokens=("manual hda retask status: not detected", "no hda-jack-retask references detected"),
    )

    mic_route_visible = _detect_bool_from_text(
        f"{readme_text}\n{public_summary_text}",
        true_tokens=("built-in microphone route is visible", "built-in mic route visibility: yes"),
        false_tokens=("built-in mic route visibility: no",),
    )

    return RepairContext(
        audit_dir=audit_dir,
        raw_dir=raw_dir,
        speaker_output_working=speaker_output_working,
        hda_retask_detected=hda_retask_detected,
        mic_route_visible=mic_route_visible,
    )


def render_hda_plan(context: RepairContext) -> str:
    speaker_state = "Speaker output currently works." if context.speaker_output_working is not False else "Speaker output state is unknown; verify manually before any change."
    retask_state = (
        "HDA retask references were detected."
        if context.hda_retask_detected is True
        else "HDA retask references are suspected; verify local audit search output manually."
    )
    mic_state = (
        "Internal mic route is visible but not proven functional."
        if context.mic_route_visible is not False
        else "Internal mic route is not confirmed; treat microphone path as unreliable."
    )

    lines = [
        "PipeTune Guided HDA Repair Plan",
        "",
        "Current state:",
        f"- {speaker_state}",
        f"- {retask_state}",
        f"- {mic_state}",
        "",
        "Do not break:",
        "- current speaker output",
        "- existing retask boot override",
        "- current PipeWire default sink/source",
        "",
        "Suspected layer:",
        "- HDA codec pin routing",
        "- ALSA/UCM routing",
        "- WirePlumber profile/route policy",
        "- capture source path",
        "",
        "Files to inspect manually:",
        f"- Audit summary directory: {context.audit_dir}",
        f"- Raw audit directory: {context.raw_dir}",
        "- /etc/modprobe.d/hda-jack-retask.conf (if present)",
        "- /lib/firmware/hda-jack-retask.fw (if present)",
        "",
        "Recommended sequence:",
        "1. Backup current retask-related files manually.",
        "2. Save current audit bundle.",
        "3. Verify speaker/headphone behavior manually.",
        "4. Verify microphone route manually.",
        "5. Inspect hdajackretask state only.",
        "6. Do not apply new pin changes yet.",
        "7. Compare codec pin nodes and UCM profile.",
        "8. Decide whether to adjust pin retask, UCM, or WirePlumber only after evidence.",
        "",
        "Backup-first strategy:",
        "- Keep timestamped backups and notes before any manual state change.",
        "- Preserve the last known-good working speaker route.",
        "",
        "Rollback requirements:",
        "- Restore backed up retask files if speaker/headphone behavior regresses.",
        "- Re-run hardware audits after rollback to confirm route recovery.",
        "",
        "Stop if:",
        "- speaker output regresses",
        "- headphone routing becomes worse",
        "- microphone route disappears",
        "- behavior becomes non-deterministic",
        "",
        "No system configuration was modified.",
    ]
    return "\n".join(lines)
