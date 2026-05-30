"""PipeTune Linux CLI."""

from __future__ import annotations

import argparse
from pathlib import Path

from pipetune import CODENAME, __version__
from pipetune.devices import collect_devices, render_devices_output
from pipetune.doctor import render_doctor_summary, run_diagnostic
from pipetune.reports.json_report import write_json_report
from pipetune.reports.markdown_report import build_markdown_report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipetune",
        description="PipeTune Linux read-only audio diagnostics.",
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

    parser.print_help()
    return 0
