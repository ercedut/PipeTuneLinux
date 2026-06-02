"""PipeTune Linux CLI."""

from __future__ import annotations

import argparse
from pathlib import Path

from pipetune import CODENAME, __version__
from pipetune.activation.installer import install_profile, render_install_dry_run, render_install_result, run_install_dry_run
from pipetune.activation.rollback import render_rollback_result, rollback_profile
from pipetune.activation.status import render_activation_status, render_installed_profiles
from pipetune.devices import collect_devices, render_devices_output
from pipetune.doctor import render_doctor_summary, run_diagnostic
from pipetune.gain.gain_audit import collect_gain_audit, render_gain_audit
from pipetune.gain.gain_recommendations import render_gain_matrix, render_gain_plan
from pipetune.hardware.hda_audit import collect_hda_audit, render_hda_audit_summary
from pipetune.hardware.mic_audit import collect_mic_audit, render_mic_audit_summary
from pipetune.hardware.quirk_report import DEFAULT_QUIRK_REPORT_DIR, create_quirk_report
from pipetune.profile.autoeq_parser import parse_autoeq_file
from pipetune.profile.pipewire_generator import write_generated_config
from pipetune.profile.validator import validate_profile
from pipetune.repair.backup_plan import render_backup_plan
from pipetune.repair.checklist import render_repair_checklist
from pipetune.repair.hda_plan import build_repair_context, render_hda_plan
from pipetune.repair.mic_test_plan import render_mic_test_plan
from pipetune.reports.json_report import write_json_report
from pipetune.reports.markdown_report import build_markdown_report
from pipetune.safety.manifest import create_profile_manifest, render_manifest_result
from pipetune.safety.preflight import (
    render_profile_preflight,
    render_profile_safety_check,
    run_profile_preflight,
    run_profile_safety_check,
)
from pipetune.safety.quirk_status import collect_hardware_quirk_metadata, render_hardware_quirk_status
from pipetune.verify.mic_analyze import analyze_wav_file, render_analysis_summary
from pipetune.verify.mic_capture import capture_microphone
from pipetune.verify.mic_plan import render_mic_verification_plan
from pipetune.verify.mic_status import render_mic_status

_SUPPORTED_FILTER_TYPES = {"PK", "LS", "HS"}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipetune",
        description="PipeTune Linux diagnostics and safe profile generation.",
    )

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("version", help="Show PipeTune Linux version information.")
    subparsers.add_parser("doctor", help="Run full system audio diagnostics.")
    subparsers.add_parser("devices", help="List detected audio devices.")

    report_parser = subparsers.add_parser("report", help="Generate markdown and JSON diagnostic reports.")
    report_parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports"),
        help="Output directory for report files (default: reports).",
    )

    profile_parser = subparsers.add_parser("profile", help="Parse, validate, and generate EQ profiles.")
    profile_subparsers = profile_parser.add_subparsers(dest="profile_command")

    parse_parser = profile_subparsers.add_parser("parse", help="Parse an AutoEQ parametric EQ file.")
    parse_parser.add_argument("autoeq_file", type=Path)

    validate_parser = profile_subparsers.add_parser("validate", help="Validate an AutoEQ parametric EQ file.")
    validate_parser.add_argument("autoeq_file", type=Path)

    generate_parser = profile_subparsers.add_parser(
        "generate", help="Generate a PipeWire filter-chain config from an AutoEQ file."
    )
    generate_parser.add_argument("autoeq_file", type=Path)
    generate_parser.add_argument("--name", required=True, help="Profile name for generated output.")
    generate_parser.add_argument(
        "--output",
        type=Path,
        default=Path("generated"),
        help="Output directory for generated config files (default: generated).",
    )

    manifest_parser = profile_subparsers.add_parser("manifest", help="Create safety manifest for generated config.")
    manifest_parser.add_argument("generated_config_file", type=Path)
    manifest_parser.add_argument("--name", required=True, help="Profile display name.")
    manifest_parser.add_argument("--type", required=True, dest="profile_type", help="Profile type.")

    safety_parser = profile_subparsers.add_parser("safety-check", help="Check generated profile safety metadata.")
    safety_parser.add_argument("generated_config_file", type=Path)

    preflight_parser = profile_subparsers.add_parser("preflight", help="Run activation readiness preflight.")
    preflight_parser.add_argument("generated_config_file", type=Path)

    dry_run_install_parser = profile_subparsers.add_parser(
        "dry-run-install", help="Preview user-level profile installation without writing files."
    )
    dry_run_install_parser.add_argument("generated_config_file", type=Path)
    dry_run_install_parser.add_argument("--user", action="store_true", help="Required user-level install target.")

    install_parser = profile_subparsers.add_parser("install", help="Install generated profile to user-level PipeWire config.")
    install_parser.add_argument("generated_config_file", type=Path)
    install_parser.add_argument("--user", action="store_true", help="Required user-level install target.")
    install_parser.add_argument("--confirm-install", action="store_true", help="Required to write user-level config.")
    install_parser.add_argument(
        "--confirm-hardware-quirk",
        action="store_true",
        help="Required when preflight needs hardware quirk confirmation.",
    )

    profile_subparsers.add_parser("list-installed", help="List PipeTune-installed user-level profiles.")
    profile_subparsers.add_parser("activation-status", help="Show PipeTune profile activation status.")

    rollback_parser = profile_subparsers.add_parser("rollback", help="Rollback a PipeTune-installed profile.")
    rollback_parser.add_argument("install_id", nargs="?")
    rollback_parser.add_argument("--latest", action="store_true", help="Rollback latest active PipeTune install.")
    rollback_parser.add_argument("--confirm-rollback", action="store_true", help="Required to modify user-level config.")

    hardware_parser = subparsers.add_parser("hardware", help="Run read-only hardware quirk audits.")
    hardware_subparsers = hardware_parser.add_subparsers(dest="hardware_command")

    hardware_subparsers.add_parser("hda-audit", help="Audit HDA codec/pin retask indicators.")
    hardware_subparsers.add_parser("mic-audit", help="Audit microphone and capture route visibility.")
    hardware_subparsers.add_parser("gain-audit", help="Audit read-only capture gain state.")
    hardware_subparsers.add_parser("quirk-status", help="Show activation-related hardware quirk status.")

    quirk_report_parser = hardware_subparsers.add_parser(
        "quirk-report", help="Create a local hardware quirk documentation bundle."
    )
    quirk_report_parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_QUIRK_REPORT_DIR,
        help=f"Output directory for the quirk report bundle (default: {DEFAULT_QUIRK_REPORT_DIR}).",
    )

    repair_parser = subparsers.add_parser("repair", help="Print guided manual repair plans.")
    repair_subparsers = repair_parser.add_subparsers(dest="repair_command")
    repair_subparsers.add_parser("hda-plan", help="Print a guided manual HDA repair strategy.")
    repair_subparsers.add_parser("backup-plan", help="Print manual backup commands for retask-related files.")
    repair_subparsers.add_parser("mic-test-plan", help="Print a safe manual microphone verification plan.")
    repair_subparsers.add_parser("gain-plan", help="Print a manual capture gain tuning plan.")
    repair_subparsers.add_parser("gain-matrix", help="Print a manual capture gain test matrix.")
    repair_subparsers.add_parser("checklist", help="Print a manual step-by-step repair checklist.")

    verify_parser = subparsers.add_parser("verify", help="Explicit verification workflows.")
    verify_subparsers = verify_parser.add_subparsers(dest="verify_command")
    verify_subparsers.add_parser("mic-plan", help="Print microphone verification plan.")

    verify_capture_parser = verify_subparsers.add_parser("mic-capture", help="Run explicit local microphone capture test.")
    verify_capture_parser.add_argument("--duration", type=int, default=5, help="Capture duration in seconds (1-30).")
    verify_capture_parser.add_argument("--output", type=Path, help="Optional output WAV path.")
    verify_capture_parser.add_argument("--confirm-recording", action="store_true", help="Required to allow recording.")
    verify_capture_parser.add_argument("--force", action="store_true", help="Allow overwrite if output file exists.")
    verify_capture_parser.add_argument("--analyze", action="store_true", help="Run mic analysis immediately after capture.")

    verify_analyze_parser = verify_subparsers.add_parser("mic-analyze", help="Analyze a local WAV recording.")
    verify_analyze_parser.add_argument("wav_file", type=Path)
    verify_analyze_parser.add_argument(
        "--update-status",
        action="store_true",
        help="Allow updating latest project mic status for files outside verification/microphone.",
    )

    verify_subparsers.add_parser("mic-status", help="Show latest microphone verification status.")

    return parser


def _cmd_version() -> int:
    print(f"PipeTune Linux v{__version__}")
    print(f"Codename: {CODENAME}")
    return 0


def _cmd_doctor() -> int:
    diagnostic = run_diagnostic()
    print(render_doctor_summary(diagnostic))
    return 0


def _cmd_devices() -> int:
    devices_data = collect_devices()
    print(render_devices_output(devices_data))
    return 0


def _cmd_report(output_dir: Path) -> int:
    diagnostic = run_diagnostic()
    output_dir.mkdir(parents=True, exist_ok=True)

    markdown_path = output_dir / "audio-diagnostic-report.md"
    json_path = output_dir / "audio-diagnostic-report.json"

    markdown_path.write_text(build_markdown_report(diagnostic), encoding="utf-8")
    write_json_report(diagnostic, json_path)

    print(str(markdown_path))
    print(str(json_path))
    return 0


def _render_filter_table() -> str:
    return f"{'Idx':<4} {'Enabled':<8} {'Type':<8} {'Freq(Hz)':>10} {'Gain(dB)':>10} {'Q':>8}"


def _cmd_profile_parse(autoeq_file: Path) -> int:
    parse_result = parse_autoeq_file(autoeq_file)
    profile = parse_result.profile

    print("AutoEQ Parse Summary")
    print(f"- Source: {autoeq_file}")
    print(f"- Profile name (inferred): {profile.name}")
    preamp_label = f"{profile.preamp_db:g} dB" if profile.preamp_db is not None else "missing"
    print(f"- Preamp: {preamp_label}")
    print(f"- Enabled filters parsed: {len(profile.filters)}")
    print("")
    print(_render_filter_table())

    for filter_item in profile.filters:
        print(
            f"{filter_item.index:<4} {'yes':<8} {filter_item.filter_type:<8} "
            f"{filter_item.frequency_hz:>10.3f} {filter_item.gain_db:>10.3f} {filter_item.q:>8.3f}"
        )

    if not profile.filters:
        print("(no enabled filters parsed)")

    if parse_result.errors:
        print("\nParse errors:")
        for error in parse_result.errors:
            print(f"- {error}")

    if profile.warnings:
        print("\nParse warnings:")
        for warning in profile.warnings:
            print(f"- {warning}")

    return 1 if parse_result.errors else 0


def _cmd_profile_validate(autoeq_file: Path) -> int:
    parse_result = parse_autoeq_file(autoeq_file)
    profile = parse_result.profile
    validation = validate_profile(parse_result)

    parse_ok = not parse_result.errors
    unsupported_types = sorted(
        {
            filter_item.filter_type
            for filter_item in profile.filters
            if filter_item.enabled and filter_item.filter_type not in _SUPPORTED_FILTER_TYPES
        }
    )

    print("AutoEQ Validation")
    print(f"- File: {autoeq_file}")
    print(f"- Parse success: {'yes' if parse_ok else 'no'}")
    print(f"- Preamp present: {'yes' if profile.preamp_db is not None else 'no'}")
    print(f"- Enabled filter count: {len(profile.filters)}")
    print(
        "- Unsupported filter types: "
        + (", ".join(unsupported_types) if unsupported_types else "none")
    )

    unsafe_gain_count = sum(1 for filter_item in profile.filters if filter_item.gain_db > 6)
    print(f"- Unsafe gain warnings (> +6 dB): {unsafe_gain_count}")

    missing_value_errors = [
        error
        for error in validation.errors
        if "missing" in error.lower() or "malformed filter line" in error.lower()
    ]
    print(f"- Missing values detected: {len(missing_value_errors)}")

    status = "PASS" if validation.valid else "FAIL"
    print(f"\nFinal status: {status}")

    if validation.errors:
        print("\nErrors:")
        for error in validation.errors:
            print(f"- {error}")

    if validation.warnings:
        print("\nWarnings:")
        for warning in validation.warnings:
            print(f"- {warning}")

    return 0 if validation.valid else 1


def _cmd_profile_generate(autoeq_file: Path, profile_name: str, output_dir: Path) -> int:
    parse_result = parse_autoeq_file(autoeq_file)
    profile = parse_result.profile
    profile.name = profile_name

    validation = validate_profile(parse_result)
    if not validation.valid:
        print("Generation failed: profile validation errors detected.")
        for error in validation.errors:
            print(f"- {error}")
        print("No system configuration was modified.")
        return 1

    output_path = write_generated_config(profile=profile, source_file=autoeq_file, output_dir=output_dir)

    print(f"Generated config: {output_path}")
    print(f"Enabled filters included: {len(profile.filters)}")

    if validation.warnings:
        print("Warnings:")
        for warning in validation.warnings:
            print(f"- {warning}")

    print("No system configuration was modified.")
    return 0


def _cmd_profile_manifest(config_file: Path, profile_name: str, profile_type: str) -> int:
    manifest_path, _manifest, errors = create_profile_manifest(config_file, profile_name, profile_type)
    print(render_manifest_result(manifest_path, errors))
    return 1 if errors else 0


def _cmd_profile_safety_check(config_file: Path) -> int:
    check = run_profile_safety_check(config_file)
    print(render_profile_safety_check(check))
    return 1 if check.errors else 0


def _cmd_profile_preflight(config_file: Path) -> int:
    result = run_profile_preflight(config_file)
    print(render_profile_preflight(result))
    return 1 if result.readiness.status == "blocked" else 0


def _cmd_profile_dry_run_install(config_file: Path, user_level: bool) -> int:
    result = run_install_dry_run(config_file, user_level=user_level)
    print(render_install_dry_run(result))
    return 0


def _cmd_profile_install(
    config_file: Path,
    user_level: bool,
    confirm_install: bool,
    confirm_hardware_quirk: bool,
) -> int:
    result = install_profile(
        config_file,
        user_level=user_level,
        confirm_install=confirm_install,
        confirm_hardware_quirk=confirm_hardware_quirk,
    )
    print(render_install_result(result))
    return result.exit_code


def _cmd_profile_list_installed() -> int:
    print(render_installed_profiles())
    return 0


def _cmd_profile_activation_status() -> int:
    print(render_activation_status())
    return 0


def _cmd_profile_rollback(install_id: str | None, latest: bool, confirm_rollback: bool) -> int:
    result = rollback_profile(install_id=install_id, latest=latest, confirm_rollback=confirm_rollback)
    print(render_rollback_result(result))
    return result.exit_code


def _cmd_hardware_hda_audit() -> int:
    result = collect_hda_audit()
    print(render_hda_audit_summary(result))
    return 0


def _cmd_hardware_mic_audit() -> int:
    result = collect_mic_audit()
    print(render_mic_audit_summary(result))
    return 0


def _cmd_hardware_gain_audit() -> int:
    result = collect_gain_audit()
    print(render_gain_audit(result))
    return 0


def _cmd_hardware_quirk_status() -> int:
    result = collect_hardware_quirk_metadata()
    print(render_hardware_quirk_status(result))
    return 0


def _cmd_hardware_quirk_report(output_dir: Path) -> int:
    report = create_quirk_report(output_dir=output_dir)
    print("Created hardware quirk report:")
    print("")
    print(f"* Public README: {report.readme_path}")
    print(f"* Public summary: {report.public_summary_path}")
    print(f"* Repair plan: {report.fix_plan_path}")
    print(f"* Local raw audit directory: {report.raw_dir}/")
    print("")
    print("Privacy note:")
    print("Raw audit files are local-only and gitignored by default.")
    print("")
    print("No system configuration was modified.")
    return 0


def _cmd_repair_hda_plan() -> int:
    context = build_repair_context()
    print(render_hda_plan(context))
    return 0


def _cmd_repair_backup_plan() -> int:
    print(render_backup_plan())
    return 0


def _cmd_repair_mic_test_plan() -> int:
    print(render_mic_test_plan())
    return 0


def _cmd_repair_gain_plan() -> int:
    print(render_gain_plan(collect_gain_audit()))
    return 0


def _cmd_repair_gain_matrix() -> int:
    print(render_gain_matrix())
    return 0


def _cmd_repair_checklist() -> int:
    print(render_repair_checklist())
    return 0


def _cmd_verify_mic_plan() -> int:
    print(render_mic_verification_plan())
    return 0


def _cmd_verify_mic_capture(
    duration: int,
    output: Path | None,
    confirm_recording: bool,
    force: bool,
    analyze: bool,
) -> int:
    result = capture_microphone(
        duration=duration,
        output_path=output,
        confirm_recording=confirm_recording,
        force=force,
        analyze=analyze,
    )
    print(result.message)
    return result.exit_code


def _cmd_verify_mic_analyze(wav_file: Path, update_status: bool) -> int:
    result = analyze_wav_file(wav_file, update_status=True if update_status else None)
    print(render_analysis_summary(result))
    if result.status == "invalid_file":
        return 1
    return 0


def _cmd_verify_mic_status() -> int:
    print(render_mic_status())
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "version":
        return _cmd_version()
    if args.command == "doctor":
        return _cmd_doctor()
    if args.command == "devices":
        return _cmd_devices()
    if args.command == "report":
        return _cmd_report(args.output)
    if args.command == "profile":
        if args.profile_command == "parse":
            return _cmd_profile_parse(args.autoeq_file)
        if args.profile_command == "validate":
            return _cmd_profile_validate(args.autoeq_file)
        if args.profile_command == "generate":
            return _cmd_profile_generate(args.autoeq_file, args.name, args.output)
        if args.profile_command == "manifest":
            return _cmd_profile_manifest(args.generated_config_file, args.name, args.profile_type)
        if args.profile_command == "safety-check":
            return _cmd_profile_safety_check(args.generated_config_file)
        if args.profile_command == "preflight":
            return _cmd_profile_preflight(args.generated_config_file)
        if args.profile_command == "dry-run-install":
            return _cmd_profile_dry_run_install(args.generated_config_file, args.user)
        if args.profile_command == "install":
            return _cmd_profile_install(
                args.generated_config_file,
                args.user,
                args.confirm_install,
                args.confirm_hardware_quirk,
            )
        if args.profile_command == "list-installed":
            return _cmd_profile_list_installed()
        if args.profile_command == "activation-status":
            return _cmd_profile_activation_status()
        if args.profile_command == "rollback":
            return _cmd_profile_rollback(args.install_id, args.latest, args.confirm_rollback)
        parser.print_help()
        return 1
    if args.command == "hardware":
        if args.hardware_command == "hda-audit":
            return _cmd_hardware_hda_audit()
        if args.hardware_command == "mic-audit":
            return _cmd_hardware_mic_audit()
        if args.hardware_command == "gain-audit":
            return _cmd_hardware_gain_audit()
        if args.hardware_command == "quirk-status":
            return _cmd_hardware_quirk_status()
        if args.hardware_command == "quirk-report":
            return _cmd_hardware_quirk_report(args.output)
        parser.print_help()
        return 1
    if args.command == "repair":
        if args.repair_command == "hda-plan":
            return _cmd_repair_hda_plan()
        if args.repair_command == "backup-plan":
            return _cmd_repair_backup_plan()
        if args.repair_command == "mic-test-plan":
            return _cmd_repair_mic_test_plan()
        if args.repair_command == "gain-plan":
            return _cmd_repair_gain_plan()
        if args.repair_command == "gain-matrix":
            return _cmd_repair_gain_matrix()
        if args.repair_command == "checklist":
            return _cmd_repair_checklist()
        parser.print_help()
        return 1
    if args.command == "verify":
        if args.verify_command == "mic-plan":
            return _cmd_verify_mic_plan()
        if args.verify_command == "mic-capture":
            return _cmd_verify_mic_capture(
                duration=args.duration,
                output=args.output,
                confirm_recording=args.confirm_recording,
                force=args.force,
                analyze=args.analyze,
            )
        if args.verify_command == "mic-analyze":
            return _cmd_verify_mic_analyze(args.wav_file, args.update_status)
        if args.verify_command == "mic-status":
            return _cmd_verify_mic_status()
        parser.print_help()
        return 1

    parser.print_help()
    return 0
