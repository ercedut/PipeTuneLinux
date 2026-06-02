"""Local tooling and offline reference DSP for the PipeTune safeguard LV2 plugin."""

from __future__ import annotations

import math
import subprocess
from dataclasses import dataclass
from pathlib import Path

from pipetune import __version__

REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_DIR = REPO_ROOT / "plugins" / "lv2" / "pipetune-safeguard.lv2"
PLUGIN_URI = "https://pipetune.local/plugins/pipetune-safeguard"
PLUGIN_NAME = "PipeTune Safeguard"

PREAMP_DEFAULT_DB = -6.0
PREAMP_MIN_DB = -24.0
PREAMP_MAX_DB = 0.0
HIGHPASS_DEFAULT_HZ = 120.0
HIGHPASS_MIN_HZ = 60.0
HIGHPASS_MAX_HZ = 250.0
LIMITER_DEFAULT_DB = -1.0
LIMITER_MIN_DB = -12.0
LIMITER_MAX_DB = -0.1
BYPASS_DEFAULT = 0.0


@dataclass(slots=True)
class OfflineValidationResult:
    passed: bool
    checks: list[str]
    errors: list[str]


def clamp(value: float | None, minimum: float, maximum: float, default: float) -> float:
    if value is None or not math.isfinite(value):
        return default
    return max(minimum, min(maximum, value))


def db_to_gain(db_value: float) -> float:
    return 10.0 ** (db_value / 20.0)


def process_reference(
    left: list[float],
    right: list[float],
    *,
    sample_rate: int = 48000,
    preamp_db: float | None = PREAMP_DEFAULT_DB,
    highpass_hz: float | None = HIGHPASS_DEFAULT_HZ,
    limiter_ceiling_db: float | None = LIMITER_DEFAULT_DB,
    bypass: float | None = BYPASS_DEFAULT,
) -> tuple[list[float], list[float]]:
    if len(left) != len(right):
        raise ValueError("Left and right inputs must have equal length.")
    if sample_rate <= 0:
        raise ValueError("Sample rate must be positive.")

    if clamp(bypass, 0.0, 1.0, BYPASS_DEFAULT) >= 0.5:
        return list(left), list(right)

    safe_preamp_db = clamp(preamp_db, PREAMP_MIN_DB, PREAMP_MAX_DB, PREAMP_DEFAULT_DB)
    safe_highpass_hz = clamp(highpass_hz, HIGHPASS_MIN_HZ, HIGHPASS_MAX_HZ, HIGHPASS_DEFAULT_HZ)
    safe_limiter_db = clamp(limiter_ceiling_db, LIMITER_MIN_DB, LIMITER_MAX_DB, LIMITER_DEFAULT_DB)

    preamp_gain = db_to_gain(safe_preamp_db)
    limiter_ceiling = db_to_gain(safe_limiter_db)
    alpha = _highpass_alpha(safe_highpass_hz, sample_rate)

    out_left: list[float] = []
    out_right: list[float] = []
    prev_in_left = 0.0
    prev_in_right = 0.0
    prev_out_left = 0.0
    prev_out_right = 0.0

    for sample_left, sample_right in zip(left, right):
        processed_left = sample_left * preamp_gain
        processed_right = sample_right * preamp_gain

        high_left = alpha * (prev_out_left + processed_left - prev_in_left)
        high_right = alpha * (prev_out_right + processed_right - prev_in_right)
        prev_in_left = processed_left
        prev_in_right = processed_right
        prev_out_left = high_left
        prev_out_right = high_right

        out_left.append(_limit(high_left, limiter_ceiling))
        out_right.append(_limit(high_right, limiter_ceiling))

    return out_left, out_right


def render_plugin_info() -> str:
    lines = [
        "PipeTune LV2 Plugin",
        f"- Name: {PLUGIN_NAME}",
        f"- Version: {__version__}",
        f"- URI: {PLUGIN_URI}",
        f"- Local bundle path: {PLUGIN_DIR}",
        "- Purpose: conservative safeguard DSP for laptop speakers and headphones.",
        "",
        "Controls:",
        f"- preamp_db: default {PREAMP_DEFAULT_DB:g} dB, range {PREAMP_MIN_DB:g} to {PREAMP_MAX_DB:g} dB",
        f"- highpass_hz: default {HIGHPASS_DEFAULT_HZ:g} Hz, range {HIGHPASS_MIN_HZ:g} to {HIGHPASS_MAX_HZ:g} Hz",
        f"- limiter_ceiling_db: default {LIMITER_DEFAULT_DB:g} dB, range {LIMITER_MIN_DB:g} to {LIMITER_MAX_DB:g} dB",
        "- bypass: default 0, range 0 to 1",
        "",
        "Safety notes:",
        "- Applies preamp/headroom before filtering.",
        "- High-pass filtering is mandatory for laptop-speaker safety.",
        "- The v0.5.0 limiter is a simple hard safety limiter, not a mastering processor.",
        "- Built artifacts are local only; PipeTune does not install, route, or activate the plugin.",
        "- No PipeWire, WirePlumber, ALSA, service, system, or user audio configuration is modified.",
    ]
    return "\n".join(lines)


def build_plugin_local() -> tuple[int, str]:
    if not PLUGIN_DIR.exists():
        return 1, f"Plugin directory is missing: {PLUGIN_DIR}"
    result = subprocess.run(
        ["make", "-C", str(PLUGIN_DIR)],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output = result.stdout
    if result.returncode != 0:
        output += (
            "\nLocal build failed. On Fedora, install build dependencies manually: "
            "gcc make lv2-devel. PipeTune did not run sudo or install packages.\n"
        )
    else:
        output += "\nLocal LV2 build completed. No global installation was performed.\n"
    return result.returncode, output


def run_offline_validation() -> OfflineValidationResult:
    checks: list[str] = []
    errors: list[str] = []
    sample_rate = 48000
    frame_count = sample_rate

    loud = [_sine(1000.0, index, sample_rate, amplitude=1.2) for index in range(frame_count)]
    limited_left, limited_right = process_reference(
        loud,
        loud,
        sample_rate=sample_rate,
        preamp_db=0.0,
        highpass_hz=120.0,
        limiter_ceiling_db=-3.0,
    )
    ceiling = db_to_gain(-3.0) + 1e-9
    if max(abs(sample) for sample in limited_left + limited_right) <= ceiling:
        checks.append("limiter ceiling respected")
    else:
        errors.append("Limiter output exceeded configured ceiling.")

    input_signal = [_sine(1000.0, index, sample_rate, amplitude=0.5) for index in range(frame_count)]
    reduced_left, _reduced_right = process_reference(
        input_signal,
        input_signal,
        sample_rate=sample_rate,
        preamp_db=-6.0,
        highpass_hz=60.0,
        limiter_ceiling_db=-0.1,
    )
    if _rms(reduced_left[1000:]) < _rms(input_signal[1000:]) * 0.55:
        checks.append("preamp reduces gain")
    else:
        errors.append("Preamp did not reduce gain as expected.")

    low = [_sine(40.0, index, sample_rate, amplitude=0.5) for index in range(frame_count)]
    mid = [_sine(1000.0, index, sample_rate, amplitude=0.5) for index in range(frame_count)]
    filtered_low, _ = process_reference(low, low, sample_rate=sample_rate, preamp_db=0.0, highpass_hz=120.0)
    filtered_mid, _ = process_reference(mid, mid, sample_rate=sample_rate, preamp_db=0.0, highpass_hz=120.0)
    if _rms(filtered_low[5000:]) < _rms(filtered_mid[5000:]) * 0.45:
        checks.append("high-pass attenuates low-frequency input")
    else:
        errors.append("High-pass filter did not attenuate low-frequency input enough.")

    bypass_left, bypass_right = process_reference(
        input_signal,
        input_signal,
        sample_rate=sample_rate,
        preamp_db=-24.0,
        highpass_hz=250.0,
        limiter_ceiling_db=-12.0,
        bypass=1.0,
    )
    if _max_abs_delta(bypass_left, input_signal) < 1e-12 and _max_abs_delta(bypass_right, input_signal) < 1e-12:
        checks.append("bypass preserves input")
    else:
        errors.append("Bypass did not preserve input within tolerance.")

    checks.append("offline validation did not install or route audio")
    return OfflineValidationResult(passed=not errors, checks=checks, errors=errors)


def render_offline_validation(result: OfflineValidationResult) -> str:
    lines = ["PipeTune LV2 Safeguard Offline Validation", ""]
    lines.append("Checks:")
    lines.extend(f"- pass: {check}" for check in result.checks)
    if result.errors:
        lines.extend(["", "Errors:"])
        lines.extend(f"- fail: {error}" for error in result.errors)
    lines.extend(
        [
            "",
            f"Final verdict: {'pass' if result.passed else 'fail'}",
            "No global LV2 installation was performed.",
            "No PipeWire, WirePlumber, ALSA, service, system, or user audio configuration was modified.",
        ]
    )
    return "\n".join(lines)


def _highpass_alpha(cutoff_hz: float, sample_rate: int) -> float:
    rc = 1.0 / (2.0 * math.pi * cutoff_hz)
    dt = 1.0 / sample_rate
    return rc / (rc + dt)


def _limit(sample: float, ceiling: float) -> float:
    return max(-ceiling, min(ceiling, sample))


def _sine(frequency_hz: float, index: int, sample_rate: int, *, amplitude: float) -> float:
    return amplitude * math.sin(2.0 * math.pi * frequency_hz * index / sample_rate)


def _rms(samples: list[float]) -> float:
    return math.sqrt(sum(sample * sample for sample in samples) / len(samples))


def _max_abs_delta(left: list[float], right: list[float]) -> float:
    return max(abs(a - b) for a, b in zip(left, right))

