"""Explicit local microphone capture command helpers."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pipetune.collectors.command import run_command
from pipetune.verify.mic_analyze import analyze_wav_file, render_analysis_summary
from pipetune.verify.models import MicCaptureResult

DEFAULT_DURATION_SECONDS = 5
MIN_DURATION_SECONDS = 1
MAX_DURATION_SECONDS = 30
DEFAULT_OUTPUT_DIR = Path("verification/microphone")


def _timestamped_output_path(output_dir: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return output_dir / f"mic-test-{stamp}.wav"


def capture_microphone(
    *,
    duration: int,
    output_path: Path | None,
    confirm_recording: bool,
    force: bool,
    analyze: bool,
) -> MicCaptureResult:
    if not confirm_recording:
        return MicCaptureResult(
            success=False,
            exit_code=1,
            message=(
                "PipeTune Microphone Capture Test\n\n"
                "Recording confirmation is required.\n"
                "Use `--confirm-recording` to proceed.\n\n"
                "No system configuration was modified."
            ),
            output_file=None,
        )

    if duration < MIN_DURATION_SECONDS or duration > MAX_DURATION_SECONDS:
        return MicCaptureResult(
            success=False,
            exit_code=1,
            message=(
                "PipeTune Microphone Capture Test\n\n"
                f"Invalid duration: {duration}. Allowed range is {MIN_DURATION_SECONDS} to {MAX_DURATION_SECONDS} seconds.\n\n"
                "No system configuration was modified."
            ),
            output_file=None,
        )

    arecord_check = run_command(["arecord", "--version"], timeout=3)
    if not arecord_check.available:
        return MicCaptureResult(
            success=False,
            exit_code=1,
            message=(
                "PipeTune Microphone Capture Test\n\n"
                "Capture failed: `arecord` is not available on this system.\n"
                "Install ALSA userspace tools manually if you want to run local capture verification.\n\n"
                "No system configuration was modified."
            ),
            output_file=None,
        )

    output_dir = output_path.parent if output_path else DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    final_output = output_path or _timestamped_output_path(output_dir)
    if final_output.exists() and not force:
        return MicCaptureResult(
            success=False,
            exit_code=1,
            message=(
                "PipeTune Microphone Capture Test\n\n"
                f"Refusing to overwrite existing file: {final_output}\n"
                "Use `--force` to allow overwrite.\n\n"
                "No system configuration was modified."
            ),
            output_file=final_output,
        )

    command = ["arecord", "-d", str(duration), "-f", "cd", "-t", "wav", str(final_output)]
    capture_result = run_command(command, timeout=float(duration + 5))

    if capture_result.timed_out:
        return MicCaptureResult(
            success=False,
            exit_code=1,
            message=(
                "PipeTune Microphone Capture Test\n\n"
                "Capture failed: recording command timed out.\n"
                f"Command: {' '.join(command)}\n\n"
                "No system configuration was modified."
            ),
            output_file=final_output,
        )

    if capture_result.exit_code != 0 or not final_output.exists():
        stderr = (capture_result.stderr or "").strip()
        reason = stderr or capture_result.error or "arecord returned a non-zero status"
        return MicCaptureResult(
            success=False,
            exit_code=1,
            message=(
                "PipeTune Microphone Capture Test\n\n"
                "Capture status:\n"
                "failed\n\n"
                f"Reason: {reason}\n\n"
                "No system configuration was modified."
            ),
            output_file=final_output,
        )

    lines = [
        "PipeTune Microphone Capture Test",
        "",
        "Privacy warning:",
        "- This command creates a local microphone recording.",
        "- Do not share the generated WAV file unless you reviewed it.",
        "",
        "Output file:",
        str(final_output),
        "",
        "Capture status:",
        "success",
        "",
        "Local audio file created. Review before sharing.",
    ]

    analysis_result = None
    if analyze:
        analysis_result = analyze_wav_file(final_output)
        lines.extend(["", render_analysis_summary(analysis_result)])

    lines.extend(["", "No system configuration was modified."])

    return MicCaptureResult(
        success=True,
        exit_code=0,
        message="\n".join(lines),
        output_file=final_output,
        analysis_result=analysis_result,
    )
