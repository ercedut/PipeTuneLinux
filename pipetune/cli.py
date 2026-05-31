"""PipeTune Linux CLI."""

from __future__ import annotations

import argparse
from pathlib import Path

from pipetune import CODENAME, __version__
from pipetune.devices import collect_devices, render_devices_output
from pipetune.doctor import render_doctor_summary, run_diagnostic
from pipetune.profile.autoeq_parser import parse_autoeq_file
from pipetune.profile.pipewire_generator import write_generated_config
from pipetune.profile.validator import validate_profile
from pipetune.reports.json_report import write_json_report
from pipetune.reports.markdown_report import build_markdown_report

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
        parser.print_help()
        return 1

    parser.print_help()
    return 0
