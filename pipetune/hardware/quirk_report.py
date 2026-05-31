"""Generate a local hardware quirk report bundle."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import shutil

from pipetune.collectors.command import run_command
from pipetune.hardware.hda_audit import (
    DEFAULT_HISTORICAL_ROUTING_ISSUE_NOTED,
    PROC_ASOUND_DIR,
    SYS_CLASS_SOUND_DIR,
    collect_hda_audit,
)
from pipetune.hardware.mic_audit import collect_mic_audit
from pipetune.hardware.sanitize import sanitize_text

DEFAULT_QUIRK_REPORT_DIR = Path("docs/system-audits/erce-hda-pin-retask")


@dataclass(slots=True)
class QuirkReportResult:
    output_dir: Path
    raw_dir: Path
    readme_path: Path
    fix_plan_path: Path
    public_summary_path: Path


def _write_command_capture(path: Path, command: list[str]) -> None:
    result = run_command(command, timeout=10)
    lines = [f"$ {' '.join(command)}", ""]

    if not result.available:
        lines.append(f"NOTE: command unavailable: {result.error}")
    elif result.timed_out:
        lines.append(f"NOTE: command timed out: {result.error}")
    else:
        lines.append(f"exit_code: {result.exit_code}")
        if result.stderr.strip():
            lines.append("")
            lines.append("stderr:")
            lines.append(result.stderr.rstrip())
        lines.append("")
        lines.append("stdout:")
        lines.append(result.stdout.rstrip() or "<empty>")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _write_file_capture(path: Path, source_file: Path, title: str) -> None:
    lines = [f"# {title}", f"source: {source_file}", ""]

    if not source_file.exists():
        lines.append("NOTE: source file not found.")
    else:
        try:
            content = source_file.read_text(encoding="utf-8", errors="replace")
            lines.append(content.rstrip() or "<empty>")
        except OSError as exc:
            lines.append(f"NOTE: failed to read source file: {exc}")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _write_pin_config_aggregate(output_file: Path, pin_file_name: str) -> None:
    lines: list[str] = []
    pin_files = sorted(SYS_CLASS_SOUND_DIR.glob(f"*/device/{pin_file_name}"))

    if not pin_files:
        lines.append(f"NOTE: no {pin_file_name} files found.")
    else:
        for pin_file in pin_files:
            lines.append(f"## {pin_file}")
            try:
                content = pin_file.read_text(encoding="utf-8", errors="replace")
                lines.append(content.rstrip() or "<empty>")
            except OSError as exc:
                lines.append(f"NOTE: failed to read: {exc}")
            lines.append("")

    output_file.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _move_path_if_exists(source: Path, destination_dir: Path) -> None:
    if not source.exists():
        return

    destination = destination_dir / source.name
    if destination.exists():
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        destination = destination_dir / f"{source.stem}-{timestamp}{source.suffix}"

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))


def _migrate_existing_raw_files(output_dir: Path, raw_dir: Path) -> None:
    raw_names = {
        "wpctl-status.txt",
        "pactl-info.txt",
        "pactl-cards.txt",
        "pactl-sinks.txt",
        "pactl-sources.txt",
        "pactl-sources-short.txt",
        "aplay-list.txt",
        "arecord-list.txt",
        "arecord-devices-long.txt",
        "asound-cards.txt",
        "asound-version.txt",
        "hda-init-pin-configs.txt",
        "hda-driver-pin-configs.txt",
        "hda-user-pin-configs.txt",
        "hda-retask-search.txt",
    }

    for name in raw_names:
        _move_path_if_exists(output_dir / name, raw_dir)

    _move_path_if_exists(output_dir / "hda-codec-files", raw_dir)


def _write_codec_files(raw_dir: Path) -> list[Path]:
    codec_output_dir = raw_dir / "hda-codec-files"
    codec_output_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    codec_files = sorted(PROC_ASOUND_DIR.glob("card*/codec#*"))
    if not codec_files:
        placeholder = codec_output_dir / "README.txt"
        placeholder.write_text("No codec# files were found under /proc/asound/card*/codec#*.\n", encoding="utf-8")
        return [placeholder]

    for codec_file in codec_files:
        safe_name = f"{codec_file.parent.name}_{codec_file.name}.txt"
        destination = codec_output_dir / safe_name
        try:
            content = codec_file.read_text(encoding="utf-8", errors="replace")
            destination.write_text(content.rstrip() + "\n", encoding="utf-8")
        except OSError as exc:
            destination.write_text(f"NOTE: failed to read {codec_file}: {exc}\n", encoding="utf-8")
        written.append(destination)

    return written


def _build_public_readme_content(output_dir: Path, raw_dir: Path) -> str:
    hda_result = collect_hda_audit(historical_routing_issue_noted=DEFAULT_HISTORICAL_ROUTING_ISSUE_NOTED)
    mic_result = collect_mic_audit()

    quirk_status = (
        "detected"
        if hda_result.manual_hda_retask_detected
        else "suspected"
        if hda_result.manual_hda_retask_suspected
        else "not detected"
    )

    lines = [
        "# HDA Pin Retask Audit Case Study (Sanitized)",
        "",
        "## 1. Summary",
        "This is a sanitized public-facing case study for a hardware audio quirk machine.",
        "Raw machine audit files are stored under `raw/` locally and intentionally gitignored.",
        "",
        "## 2. Observed Historical Behavior",
        "- This machine has suspected manual HDA pin retask/routing quirk behavior.",
        "- Speaker output currently works and must not be broken.",
        "- Built-in microphone route is visible but not proven functional.",
        "- Capture test has not been performed.",
        "",
        "## 3. Current PipeTune Interpretation",
        f"- Hardware quirk status: {quirk_status}.",
        "- Do not auto-apply speaker/headphone profiles without manual output confirmation.",
        "- Built-in microphone should be treated as unreliable until manual capture verification is completed.",
        "",
        "## 4. Why This Is Not a DSP Problem",
        "- The issue pattern is consistent with HDA codec pin routing and route policy behavior.",
        "- EQ/DSP profile generation cannot correct hardware pin assignment mismatches.",
        "",
        "## 5. Risk for Future PipeTune Features",
        "- Future profile logic must include hardware-quirk metadata guardrails.",
        "- Automatic route assumptions are unsafe on this machine class.",
        "",
        "## 6. Safe Rules for This Machine",
        "- Keep all commands read-only by default.",
        "- Do not auto-apply output profiles without manual confirmation.",
        "- Do not use built-in microphone as a calibration source.",
        "- Prefer external USB or measurement microphones for calibration workflows.",
        "",
        "## 7. Collected Files",
        f"- Public README: {output_dir / 'README.md'}",
        f"- Public summary: {output_dir / 'PUBLIC_SUMMARY.md'}",
        f"- Repair plan: {output_dir / 'FIX_PLAN.md'}",
        f"- Local raw audit directory: {raw_dir}",
        "",
        "## 8. Next Diagnostic Steps",
        "- Review `FIX_PLAN.md` before any manual state-changing action.",
        "- Review local `raw/` captures before sharing anything externally.",
        "- Run manual speaker/headphone and mic verification outside PipeTune when approved.",
    ]

    return sanitize_text("\n".join(lines) + "\n")


def _build_fix_plan_content() -> str:
    text = """# HDA Pin Retask and Internal Microphone Repair Plan

## 1. Current Known State
- Speaker output currently works with historical/manual retask context.
- Headphone auto-switch behavior may still be unreliable.
- Built-in internal microphone route is visible but not proven functional without capture test.

## 2. What Must Not Be Broken
- Do not break current speaker output.
- Do not erase or overwrite existing manual retask state blindly.
- Do not assume built-in mic is valid for calibration.

## 3. Likely Root Causes
- HDA codec pin assignment mismatch (speaker/headphone routing quirk).
- Persisted retask override interactions with ALSA/UCM profile selection.
- WirePlumber/PipeWire route selection exposing unstable source/sink defaults.

## 4. Read-Only Checks Already Collected
- ALSA/PipeWire command snapshots (`pactl`, `wpctl`, `aplay`, `arecord`) in local `raw/`.
- `/proc/asound` snapshots and codec file copies when readable.
- HDA pin config visibility (`init_pin_configs`, `driver_pin_configs`, `user_pin_configs`).
- Retask-reference search under `/etc/modprobe.d` and `/lib/firmware`.

## 5. Manual Verification Checklist
- Confirm speaker output path still works.
- Confirm headphone insertion/removal switching behavior.
- Confirm source mute/state/default source values.
- Confirm whether internal mic route appears and can capture signal.

## 6. Safe Repair Strategy
- Keep all current working state intact until backups are complete.
- Perform only one manual change at a time.
- After each change, re-run read-only audit and manual output checks.
- Stop immediately if speaker route regresses.

## 7. hdajackretask Investigation Path
- MANUAL / DO NOT RUN WITHOUT CONFIRMATION: Open `hdajackretask` for inspection only.
- MANUAL / DO NOT RUN WITHOUT CONFIRMATION: Check whether any boot override is currently enabled.
- MANUAL / DO NOT RUN WITHOUT CONFIRMATION: Back up `/etc/modprobe.d/hda-jack-retask.conf` if present.
- MANUAL / DO NOT RUN WITHOUT CONFIRMATION: Back up `/lib/firmware/hda-jack-retask.fw` if present.
- Do not apply new retask pins until speaker/headphone mapping is documented first.

## 8. ALSA UCM Investigation Path
- Read-only: inspect available UCM2 profile definitions for this codec/card.
- Read-only: compare capture/playback controls exposed before/after manual tests.
- If UCM mapping conflicts are found, plan controlled manual adjustments with rollback notes first.

## 9. WirePlumber/PipeWire Route Investigation Path
- Read-only: verify default sink/source consistency from `pactl` and `wpctl` outputs.
- Read-only: inspect route visibility and profile mode transitions during jack events.
- Avoid policy changes until hardware pin behavior is confirmed stable.

## 10. Built-in Microphone Investigation Path
- Read-only first: confirm internal mic source names and states.
- MANUAL / DO NOT RUN WITHOUT CONFIRMATION: perform short user-approved capture test outside PipeTune.
- If internal mic remains broken, treat built-in mic as unreliable for calibration.

## 11. Rollback Strategy
- Keep backups of any retask-related files before changing them.
- Maintain a chronological change log with timestamped audit outputs.
- If regression occurs, restore last known-good manual retask configuration.

## 12. When to Stop
- Stop when speaker routing regresses.
- Stop when behavior becomes non-deterministic after a change.
- Stop and escalate to controlled manual hardware debug if internal mic remains unavailable after safe checks.
"""
    return sanitize_text(text)


def _build_public_summary_content(output_dir: Path, raw_dir: Path) -> str:
    hda_result = collect_hda_audit(historical_routing_issue_noted=DEFAULT_HISTORICAL_ROUTING_ISSUE_NOTED)
    mic_result = collect_mic_audit()

    lines = [
        "# PUBLIC SUMMARY",
        "",
        "## Privacy Statement",
        "This summary is sanitized for repository sharing.",
        "Raw audit files are local-only, stored under `raw/`, and gitignored by default.",
        "PipeTune does not send audit data anywhere.",
        "",
        "## Technical Finding",
        f"- Manual HDA retask status: {'detected' if hda_result.manual_hda_retask_detected else 'suspected' if hda_result.manual_hda_retask_suspected else 'not detected'}",
        f"- Built-in mic route visibility: {mic_result.internal_mic_route_visible}",
        "- Capture test performed: no",
        "",
        "## Next Manual Steps",
        "- Confirm speaker/headphone behavior manually before any profile application.",
        "- Review `FIX_PLAN.md` and local `raw/` data before manual system changes.",
        "- Use an external microphone for calibration workflows until built-in mic is validated.",
        "",
        "## What Was Not Modified",
        "- No system audio configuration was modified.",
        "- No HDA pin override was written.",
        "- No PipeWire/WirePlumber/ALSA restart was performed.",
        "",
        f"Public files: {output_dir / 'README.md'}, {output_dir / 'PUBLIC_SUMMARY.md'}, {output_dir / 'FIX_PLAN.md'}",
        f"Local raw directory: {raw_dir}",
    ]
    return sanitize_text("\n".join(lines) + "\n")


def create_quirk_report(output_dir: Path = DEFAULT_QUIRK_REPORT_DIR) -> QuirkReportResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / ".gitkeep").touch(exist_ok=True)

    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / ".gitkeep").touch(exist_ok=True)

    _migrate_existing_raw_files(output_dir, raw_dir)

    _write_command_capture(raw_dir / "wpctl-status.txt", ["wpctl", "status"])
    _write_command_capture(raw_dir / "pactl-info.txt", ["pactl", "info"])
    _write_command_capture(raw_dir / "pactl-cards.txt", ["pactl", "list", "cards"])
    _write_command_capture(raw_dir / "pactl-sinks.txt", ["pactl", "list", "sinks"])
    _write_command_capture(raw_dir / "pactl-sources.txt", ["pactl", "list", "sources"])
    _write_command_capture(raw_dir / "pactl-sources-short.txt", ["pactl", "list", "sources", "short"])
    _write_command_capture(raw_dir / "aplay-list.txt", ["aplay", "-l"])
    _write_command_capture(raw_dir / "arecord-list.txt", ["arecord", "-l"])
    _write_command_capture(raw_dir / "arecord-devices-long.txt", ["arecord", "-L"])

    _write_file_capture(raw_dir / "asound-cards.txt", PROC_ASOUND_DIR / "cards", "ALSA cards")
    _write_file_capture(raw_dir / "asound-version.txt", PROC_ASOUND_DIR / "version", "ALSA version")

    _write_pin_config_aggregate(raw_dir / "hda-init-pin-configs.txt", "init_pin_configs")
    _write_pin_config_aggregate(raw_dir / "hda-driver-pin-configs.txt", "driver_pin_configs")
    _write_pin_config_aggregate(raw_dir / "hda-user-pin-configs.txt", "user_pin_configs")

    _write_codec_files(raw_dir)

    hda_result = collect_hda_audit(historical_routing_issue_noted=DEFAULT_HISTORICAL_ROUTING_ISSUE_NOTED)
    retask_lines = ["# HDA retask reference search", ""]
    if hda_result.retask_reference_hits:
        retask_lines.extend(hda_result.retask_reference_hits)
    else:
        retask_lines.append("No hda-jack-retask references detected.")
    if hda_result.retask_reference_search_errors:
        retask_lines.append("")
        retask_lines.append("Warnings:")
        for warning in hda_result.retask_reference_search_errors:
            retask_lines.append(f"- {warning}")
    (raw_dir / "hda-retask-search.txt").write_text("\n".join(retask_lines).rstrip() + "\n", encoding="utf-8")

    readme_path = output_dir / "README.md"
    fix_plan_path = output_dir / "FIX_PLAN.md"
    public_summary_path = output_dir / "PUBLIC_SUMMARY.md"

    readme_path.write_text(_build_public_readme_content(output_dir, raw_dir), encoding="utf-8")
    fix_plan_path.write_text(_build_fix_plan_content(), encoding="utf-8")
    public_summary_path.write_text(_build_public_summary_content(output_dir, raw_dir), encoding="utf-8")

    return QuirkReportResult(
        output_dir=output_dir,
        raw_dir=raw_dir,
        readme_path=readme_path,
        fix_plan_path=fix_plan_path,
        public_summary_path=public_summary_path,
    )
