"""Local tooling and offline reference DSP for the PipeTune safeguard LV2 plugin."""

from __future__ import annotations

import math
import ctypes
import json
import re
import shutil
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
PLUGIN_SHARED_OBJECT = "pipetune_safeguard.so"
FEDORA_BUILD_INSTRUCTIONS = "sudo dnf install gcc make lv2-devel"
PLUGIN_SAFETY_DISCLAIMER = [
    "No global LV2 installation was performed.",
    "No audio routing was changed.",
    "No PipeWire, WirePlumber, ALSA, service, system, or user audio configuration was modified.",
]
SOURCE_FILES = {
    "manifest.ttl",
    "pipetune-safeguard.ttl",
    "pipetune_safeguard.c",
    "Makefile",
}
LOCAL_ARTIFACT_PATTERNS = ("*.so", "*.o", "*.d", "*.tmp", "*~")
CONTROL_RANGES = {
    "preamp_db": (PREAMP_MIN_DB, PREAMP_MAX_DB),
    "highpass_hz": (HIGHPASS_MIN_HZ, HIGHPASS_MAX_HZ),
    "limiter_ceiling_db": (LIMITER_MIN_DB, LIMITER_MAX_DB),
    "bypass": (0.0, 1.0),
}


@dataclass(slots=True)
class OfflineValidationResult:
    passed: bool
    checks: list[str]
    warnings: list[str]
    errors: list[str]


@dataclass(slots=True)
class PluginValidationReport:
    passed: bool
    checks: list[str]
    warnings: list[str]
    errors: list[str]


@dataclass(slots=True)
class PluginCleanResult:
    removed: list[Path]
    preserved: list[Path]
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
        "- The limiter is a simple hard safety limiter, not a mastering processor.",
        "- Built artifacts are local only; PipeTune does not install, route, or activate the plugin.",
        "",
        *PLUGIN_SAFETY_DISCLAIMER,
    ]
    return "\n".join(lines)


def render_plugin_safety_disclaimer() -> str:
    return "\n".join(PLUGIN_SAFETY_DISCLAIMER)


def check_build_dependencies() -> PluginValidationReport:
    checks: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []

    if shutil.which("gcc") is None:
        errors.append("Missing build dependency: gcc.")
    else:
        checks.append("gcc found")

    if shutil.which("make") is None:
        errors.append("Missing build dependency: make.")
    else:
        checks.append("make found")

    if _lv2_headers_available():
        checks.append("LV2 development headers found")
    else:
        errors.append("Missing build dependency: LV2 development headers (lv2-devel).")

    return PluginValidationReport(passed=not errors, checks=checks, warnings=warnings, errors=errors)


def build_plugin_local() -> tuple[int, str]:
    if not PLUGIN_DIR.exists():
        return 1, f"Plugin directory is missing: {PLUGIN_DIR}"

    dependency_report = check_build_dependencies()
    if not dependency_report.passed:
        lines = ["Local LV2 build refused: missing build dependencies.", ""]
        lines.extend(f"- pass: {check}" for check in dependency_report.checks)
        lines.extend(f"- fail: {error}" for error in dependency_report.errors)
        lines.extend(
            [
                "",
                "Install Fedora build dependencies manually:",
                FEDORA_BUILD_INSTRUCTIONS,
                "",
                "PipeTune did not run sudo or install packages.",
                "No global LV2 installation was performed.",
                "No audio routing was changed.",
                "No PipeWire, WirePlumber, ALSA, service, system, or user audio configuration was modified.",
            ]
        )
        return 1, "\n".join(lines)

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
            "\nLocal build failed. On Fedora, install build dependencies manually:\n"
            f"{FEDORA_BUILD_INSTRUCTIONS}\n"
            "PipeTune did not run sudo or install packages.\n"
        )
    else:
        output += (
            f"\nLocal LV2 build completed. Artifacts are in: {PLUGIN_DIR}\n"
            f"- {PLUGIN_DIR / PLUGIN_SHARED_OBJECT}\n"
            f"{render_plugin_safety_disclaimer()}\n"
        )
    return result.returncode, output


def clean_plugin_local() -> PluginCleanResult:
    removed: list[Path] = []
    preserved = [PLUGIN_DIR / source_file for source_file in sorted(SOURCE_FILES)]
    errors: list[str] = []

    if not PLUGIN_DIR.exists():
        return PluginCleanResult(removed=removed, preserved=preserved, errors=[f"Plugin directory is missing: {PLUGIN_DIR}"])

    for pattern in LOCAL_ARTIFACT_PATTERNS:
        for artifact in PLUGIN_DIR.glob(pattern):
            if artifact.name in SOURCE_FILES:
                continue
            if not artifact.is_file():
                continue
            try:
                artifact.unlink()
                removed.append(artifact)
            except OSError as exc:
                errors.append(f"Could not remove {artifact}: {exc}")

    return PluginCleanResult(removed=sorted(removed), preserved=preserved, errors=errors)


def render_clean_result(result: PluginCleanResult) -> str:
    lines = ["PipeTune LV2 Safeguard Local Clean", ""]
    if result.removed:
        lines.append("Removed local build artifacts:")
        lines.extend(f"- {path}" for path in result.removed)
    else:
        lines.append("No local build artifacts were found.")
    lines.extend(["", "Preserved source files:"])
    lines.extend(f"- {path}" for path in result.preserved)
    if result.errors:
        lines.extend(["", "Errors:"])
        lines.extend(f"- {error}" for error in result.errors)
    lines.extend(["", *PLUGIN_SAFETY_DISCLAIMER])
    return "\n".join(lines)


def run_offline_validation() -> OfflineValidationResult:
    checks: list[str] = []
    warnings: list[str] = []
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

    compiled_checks, compiled_warnings, compiled_errors = _run_compiled_plugin_validation()
    checks.extend(compiled_checks)
    warnings.extend(compiled_warnings)
    errors.extend(compiled_errors)

    checks.append("offline validation did not install or route audio")
    return OfflineValidationResult(passed=not errors, checks=checks, warnings=warnings, errors=errors)


def render_offline_validation(result: OfflineValidationResult) -> str:
    lines = ["PipeTune LV2 Safeguard Offline Validation", ""]
    lines.append("Checks:")
    lines.extend(f"- pass: {check}" for check in result.checks)
    if result.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- warn: {warning}" for warning in result.warnings)
    if result.errors:
        lines.extend(["", "Errors:"])
        lines.extend(f"- fail: {error}" for error in result.errors)
    lines.extend(["", f"Final verdict: {'pass' if result.passed else 'fail'}", *PLUGIN_SAFETY_DISCLAIMER])
    return "\n".join(lines)


def run_metadata_validation() -> PluginValidationReport:
    checks: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []

    manifest_path = PLUGIN_DIR / "manifest.ttl"
    ttl_path = PLUGIN_DIR / "pipetune-safeguard.ttl"
    manifest = ""
    ttl = ""

    if manifest_path.exists():
        checks.append("manifest.ttl exists")
        manifest = manifest_path.read_text(encoding="utf-8")
    else:
        errors.append(f"Missing metadata file: {manifest_path}")

    if ttl_path.exists():
        checks.append("pipetune-safeguard.ttl exists")
        ttl = ttl_path.read_text(encoding="utf-8")
    else:
        errors.append(f"Missing metadata file: {ttl_path}")

    if manifest and ttl:
        if PLUGIN_URI in manifest and PLUGIN_URI in ttl:
            checks.append("plugin URI is consistent between CLI metadata and TTL files")
        else:
            errors.append("Plugin URI is inconsistent between CLI metadata and TTL files.")

        for symbol in ("in_l", "in_r", "out_l", "out_r", "preamp_db", "highpass_hz", "limiter_ceiling_db", "bypass"):
            if f'lv2:symbol "{symbol}"' in ttl and _port_block_has_name(ttl, symbol):
                checks.append(f"port documented: {symbol}")
            else:
                errors.append(f"Port is not fully documented in TTL metadata: {symbol}")

        for symbol, (minimum, maximum) in CONTROL_RANGES.items():
            block = _extract_port_block(ttl, symbol)
            if not block:
                errors.append(f"Control range is missing for {symbol}.")
                continue
            if _ttl_number_present(block, "lv2:minimum", minimum) and _ttl_number_present(block, "lv2:maximum", maximum):
                checks.append(f"control range documented: {symbol} {minimum:g} to {maximum:g}")
            else:
                errors.append(f"Control range mismatch for {symbol}; expected {minimum:g} to {maximum:g}.")

    lv2_validate = shutil.which("lv2_validate")
    if lv2_validate is None:
        warnings.append(
            "lv2_validate is not installed; skipped optional external LV2 metadata validation. "
            f"On Fedora, install LV2 tooling with: {FEDORA_BUILD_INSTRUCTIONS}"
        )
    else:
        result = subprocess.run(
            [lv2_validate, str(manifest_path), str(ttl_path)],
            cwd=PLUGIN_DIR,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if result.returncode == 0:
            checks.append("lv2_validate passed")
        else:
            failure_kind = _classify_lv2_validate_failure(result.stdout)
            if failure_kind == "missing_helper":
                warnings.append(
                    "External lv2_validate is installed but its helper dependency is missing; "
                    "internal metadata checks passed. "
                    f"lv2_validate output: {result.stdout.strip()}"
                )
            else:
                errors.append("lv2_validate failed:\n" + result.stdout.strip())

    return PluginValidationReport(passed=not errors, checks=checks, warnings=warnings, errors=errors)


def render_metadata_validation(report: PluginValidationReport, *, json_output: bool = False) -> str:
    if json_output:
        payload = {
            "passed": report.passed,
            "checks": report.checks,
            "warnings": report.warnings,
            "errors": report.errors,
            "safety": PLUGIN_SAFETY_DISCLAIMER,
        }
        return json.dumps(payload, indent=2, sort_keys=True)
    return _render_validation_report("PipeTune LV2 Safeguard Metadata Validation", report)


def run_rt_safety_validation(source_path: Path | None = None) -> PluginValidationReport:
    checks: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []
    source_path = PLUGIN_DIR / "pipetune_safeguard.c" if source_path is None else source_path

    if not source_path.exists():
        return PluginValidationReport(False, checks, warnings, [f"Missing source file: {source_path}"])

    source = source_path.read_text(encoding="utf-8")
    uncommented = _strip_c_comments(source)
    run_body = _extract_c_function_body(uncommented, "run")
    if run_body is None:
        errors.append("Could not find LV2 run() processing callback.")
        return PluginValidationReport(False, checks, warnings, errors)

    forbidden = (
        "malloc",
        "calloc",
        "realloc",
        "free",
        "printf",
        "fprintf",
        "fopen",
        "open",
        "read",
        "write",
        "system",
        "popen",
        "sleep",
        "pthread_create",
    )
    forbidden_hits = [name for name in forbidden if re.search(rf"\b{name}\s*\(", run_body)]
    if forbidden_hits:
        errors.append("Forbidden non-RT-safe calls found in run(): " + ", ".join(forbidden_hits))
    else:
        checks.append("run() contains no obvious heap allocation, file I/O, logging, sleep, thread creation, or system calls")

    expected_clamps = {
        "bypass": ("0.0f", "1.0f"),
        "preamp_db": ("-24.0f", "0.0f"),
        "highpass_hz": ("60.0f", "250.0f"),
        "limiter_ceiling_db": ("-12.0f", "-0.1f"),
    }
    for control, (minimum, maximum) in expected_clamps.items():
        if control in run_body and "clampf" in run_body and minimum in run_body and maximum in run_body:
            checks.append(f"unsafe control values are clamped: {control}")
        else:
            errors.append(f"Missing or incomplete clamp for control: {control}")

    if "read_control" in run_body and "isfinite" in uncommented:
        checks.append("missing or non-finite controls have safe fallback handling")
    else:
        errors.append("Missing safe fallback handling for missing or non-finite controls.")

    return PluginValidationReport(passed=not errors, checks=checks, warnings=warnings, errors=errors)


def render_rt_safety_validation(report: PluginValidationReport) -> str:
    return _render_validation_report("PipeTune LV2 Safeguard RT-Safety Validation", report)


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


def _render_validation_report(title: str, report: PluginValidationReport) -> str:
    lines = [title, "", "Checks:"]
    if report.checks:
        lines.extend(f"- pass: {check}" for check in report.checks)
    else:
        lines.append("- none")
    if report.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- warn: {warning}" for warning in report.warnings)
    if report.errors:
        lines.extend(["", "Errors:"])
        lines.extend(f"- fail: {error}" for error in report.errors)
    lines.extend(["", f"Final verdict: {'pass' if report.passed else 'fail'}", *PLUGIN_SAFETY_DISCLAIMER])
    return "\n".join(lines)


def _lv2_headers_available() -> bool:
    pkg_config = shutil.which("pkg-config")
    if pkg_config is not None:
        result = subprocess.run(
            [pkg_config, "--exists", "lv2"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            return True
    return any(
        candidate.exists()
        for candidate in (
            Path("/usr/include/lv2/core/lv2.h"),
            Path("/usr/local/include/lv2/core/lv2.h"),
        )
    )


def _extract_port_block(ttl: str, symbol: str) -> str:
    marker = f'lv2:symbol "{symbol}"'
    marker_index = ttl.find(marker)
    if marker_index == -1:
        return ""
    start = ttl.rfind("[", 0, marker_index)
    end = ttl.find("]", marker_index)
    if start == -1 or end == -1:
        return ""
    return ttl[start : end + 1]


def _port_block_has_name(ttl: str, symbol: str) -> bool:
    block = _extract_port_block(ttl, symbol)
    return bool(block and re.search(r'lv2:name\s+"[^"]+"', block))


def _ttl_number_present(block: str, predicate: str, expected: float) -> bool:
    match = re.search(rf"{re.escape(predicate)}\s+(-?\d+(?:\.\d+)?)", block)
    return bool(match and math.isclose(float(match.group(1)), expected, abs_tol=1e-9))


def _strip_c_comments(source: str) -> str:
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"//.*", "", source)


def _extract_c_function_body(source: str, function_name: str) -> str | None:
    match = re.search(rf"\b{re.escape(function_name)}\s*\([^)]*\)\s*\{{", source)
    if match is None:
        return None
    index = match.end()
    depth = 1
    while index < len(source):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[match.end() : index]
        index += 1
    return None


_LV2_VALIDATE_MISSING_HELPER_PATTERNS = (
    ": not found",
    "no such file or directory",
    "command not found",
    "cannot find",
    "missing validator",
)


def _classify_lv2_validate_failure(output: str) -> str:
    """Classify lv2_validate failure output.

    Returns "missing_helper" when the output indicates the validator's helper
    tool (e.g., sord_validate) is absent — a broken environment, not a real
    TTL error.  Returns "actual_failure" for genuine validation errors.
    """
    lower = output.lower()
    for pattern in _LV2_VALIDATE_MISSING_HELPER_PATTERNS:
        if pattern in lower:
            return "missing_helper"
    return "actual_failure"


def _run_compiled_plugin_validation() -> tuple[list[str], list[str], list[str]]:
    shared_object = PLUGIN_DIR / PLUGIN_SHARED_OBJECT
    if not shared_object.exists():
        return [], [f"Compiled plugin artifact not found at {shared_object}; run pipetune plugin build --local for compiled validation."], []

    try:
        harness = _CompiledLV2Harness(shared_object)
        checks = harness.run_checks()
    except Exception as exc:  # noqa: BLE001 - validation reports failures instead of crashing CLI.
        return [], [], [f"Compiled plugin validation failed: {exc}"]
    return checks, [], []


class _CompiledLV2Harness:
    def __init__(self, shared_object: Path) -> None:
        self.shared_object = shared_object
        self.sample_rate = 48000
        self._lib = ctypes.CDLL(str(shared_object))
        self._descriptor_ptr_type, self._descriptor_type = self._build_descriptor_type()
        descriptor_func = self._lib.lv2_descriptor
        descriptor_func.argtypes = [ctypes.c_uint32]
        descriptor_func.restype = self._descriptor_ptr_type
        descriptor_ptr = descriptor_func(0)
        if not descriptor_ptr:
            raise RuntimeError("lv2_descriptor(0) returned NULL")
        self.descriptor = descriptor_ptr.contents
        uri = self.descriptor.URI.decode("utf-8") if self.descriptor.URI else ""
        if uri != PLUGIN_URI:
            raise RuntimeError(f"descriptor URI mismatch: {uri}")

    @staticmethod
    def _build_descriptor_type() -> tuple[type[ctypes.POINTER], type[ctypes.Structure]]:
        class LV2Descriptor(ctypes.Structure):
            pass

        descriptor_ptr = ctypes.POINTER(LV2Descriptor)
        instantiate_type = ctypes.CFUNCTYPE(
            ctypes.c_void_p,
            descriptor_ptr,
            ctypes.c_double,
            ctypes.c_char_p,
            ctypes.c_void_p,
        )
        connect_type = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p)
        activate_type = ctypes.CFUNCTYPE(None, ctypes.c_void_p)
        run_type = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_uint32)
        deactivate_type = ctypes.CFUNCTYPE(None, ctypes.c_void_p)
        cleanup_type = ctypes.CFUNCTYPE(None, ctypes.c_void_p)
        extension_type = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_char_p)
        LV2Descriptor._fields_ = [
            ("URI", ctypes.c_char_p),
            ("instantiate", instantiate_type),
            ("connect_port", connect_type),
            ("activate", activate_type),
            ("run", run_type),
            ("deactivate", deactivate_type),
            ("cleanup", cleanup_type),
            ("extension_data", extension_type),
        ]
        return descriptor_ptr, LV2Descriptor

    def run_checks(self) -> list[str]:
        checks: list[str] = ["compiled LV2 descriptor loads"]
        frame_count = self.sample_rate

        loud = [_sine(1000.0, index, self.sample_rate, amplitude=1.2) for index in range(frame_count)]
        out_l, out_r = self._run_plugin(loud, loud, preamp_db=0.0, highpass_hz=120.0, limiter_ceiling_db=-3.0, bypass=0.0)
        ceiling = db_to_gain(-3.0) + 1e-6
        if max(abs(sample) for sample in out_l + out_r) > ceiling:
            raise RuntimeError("compiled limiter output exceeded configured ceiling")
        checks.append("compiled limiter ceiling respected")

        signal = [_sine(1000.0, index, self.sample_rate, amplitude=0.5) for index in range(frame_count)]
        reduced_l, _ = self._run_plugin(signal, signal, preamp_db=-6.0, highpass_hz=60.0, limiter_ceiling_db=-0.1, bypass=0.0)
        if _rms(reduced_l[1000:]) >= _rms(signal[1000:]) * 0.56:
            raise RuntimeError("compiled preamp did not reduce gain as expected")
        checks.append("compiled preamp reduces gain")

        low = [_sine(40.0, index, self.sample_rate, amplitude=0.5) for index in range(frame_count)]
        mid = [_sine(1000.0, index, self.sample_rate, amplitude=0.5) for index in range(frame_count)]
        low_l, _ = self._run_plugin(low, low, preamp_db=0.0, highpass_hz=120.0, limiter_ceiling_db=-0.1, bypass=0.0)
        mid_l, _ = self._run_plugin(mid, mid, preamp_db=0.0, highpass_hz=120.0, limiter_ceiling_db=-0.1, bypass=0.0)
        if _rms(low_l[5000:]) >= _rms(mid_l[5000:]) * 0.45:
            raise RuntimeError("compiled high-pass did not attenuate low-frequency input enough")
        checks.append("compiled high-pass attenuates low-frequency input")

        right = [_sine(700.0, index, self.sample_rate, amplitude=0.25) for index in range(frame_count)]
        bypass_l, bypass_r = self._run_plugin(signal, right, preamp_db=-24.0, highpass_hz=250.0, limiter_ceiling_db=-12.0, bypass=1.0)
        if _max_abs_delta(bypass_l, signal) >= 1e-7 or _max_abs_delta(bypass_r, right) >= 1e-7:
            raise RuntimeError("compiled bypass did not preserve stereo input")
        checks.append("compiled bypass preserves stereo input")

        boundary_inputs = [
            (PREAMP_MIN_DB - 10.0, HIGHPASS_DEFAULT_HZ, LIMITER_DEFAULT_DB, -1.0),
            (PREAMP_MAX_DB + 10.0, HIGHPASS_DEFAULT_HZ, LIMITER_DEFAULT_DB, 2.0),
            (PREAMP_DEFAULT_DB, HIGHPASS_MIN_HZ - 10.0, LIMITER_DEFAULT_DB, 0.0),
            (PREAMP_DEFAULT_DB, HIGHPASS_MAX_HZ + 100.0, LIMITER_DEFAULT_DB, 0.0),
            (PREAMP_DEFAULT_DB, HIGHPASS_DEFAULT_HZ, LIMITER_MIN_DB - 10.0, 0.0),
            (PREAMP_DEFAULT_DB, HIGHPASS_DEFAULT_HZ, LIMITER_MAX_DB + 10.0, 0.0),
            (math.nan, math.nan, math.nan, math.nan),
        ]
        short = signal[:1024]
        for preamp_db, highpass_hz, limiter_db, bypass in boundary_inputs:
            self._run_plugin(short, short, preamp_db=preamp_db, highpass_hz=highpass_hz, limiter_ceiling_db=limiter_db, bypass=bypass)
        checks.append("compiled plugin does not crash on boundary or non-finite control values")

        return checks

    def _run_plugin(
        self,
        left: list[float],
        right: list[float],
        *,
        preamp_db: float,
        highpass_hz: float,
        limiter_ceiling_db: float,
        bypass: float,
    ) -> tuple[list[float], list[float]]:
        if len(left) != len(right):
            raise ValueError("Left and right buffers must have equal length.")

        frame_count = len(left)
        float_array = ctypes.c_float * frame_count
        in_l = float_array(*left)
        in_r = float_array(*right)
        out_l = float_array()
        out_r = float_array()
        preamp = ctypes.c_float(preamp_db)
        highpass = ctypes.c_float(highpass_hz)
        limiter = ctypes.c_float(limiter_ceiling_db)
        bypass_value = ctypes.c_float(bypass)

        instance = self.descriptor.instantiate(
            ctypes.pointer(self.descriptor),
            ctypes.c_double(self.sample_rate),
            str(PLUGIN_DIR).encode("utf-8"),
            None,
        )
        if not instance:
            raise RuntimeError("instantiate returned NULL")
        try:
            self.descriptor.connect_port(instance, 0, ctypes.cast(in_l, ctypes.c_void_p))
            self.descriptor.connect_port(instance, 1, ctypes.cast(in_r, ctypes.c_void_p))
            self.descriptor.connect_port(instance, 2, ctypes.cast(out_l, ctypes.c_void_p))
            self.descriptor.connect_port(instance, 3, ctypes.cast(out_r, ctypes.c_void_p))
            self.descriptor.connect_port(instance, 4, ctypes.cast(ctypes.pointer(preamp), ctypes.c_void_p))
            self.descriptor.connect_port(instance, 5, ctypes.cast(ctypes.pointer(highpass), ctypes.c_void_p))
            self.descriptor.connect_port(instance, 6, ctypes.cast(ctypes.pointer(limiter), ctypes.c_void_p))
            self.descriptor.connect_port(instance, 7, ctypes.cast(ctypes.pointer(bypass_value), ctypes.c_void_p))
            self.descriptor.activate(instance)
            self.descriptor.run(instance, frame_count)
            self.descriptor.deactivate(instance)
        finally:
            self.descriptor.cleanup(instance)

        return list(out_l), list(out_r)
