"""Bluetooth policy diagnostics for PipeTune Linux."""

from __future__ import annotations

import datetime
import json
import socket
from dataclasses import dataclass, field

import pipetune
from pipetune.wireplumber.collect import collect_pactl_cards, collect_wpctl_status
from pipetune.wireplumber.diagnose import _detect_bluetooth_profile


_HFP_HSP_MARKERS = ("HSP/HFP", "hfp", "hsp", "HSP", "HFP", "headset", "Headset")
_A2DP_MARKERS = ("A2DP", "a2dp", "Advanced Audio", "advanced-audio")
_BLUETOOTH_DEVICE_MARKERS = ("bluez", "bluetooth", "Bluetooth", "BlueTooth", "BT", "[bluez]")
_CODEC_HINTS = ("SBC", "AAC", "aptX", "LDAC", "LC3", "mSBC")

_SAFETY_DISCLAIMER = [
    "No Bluetooth profile was changed.",
    "No system configuration was modified.",
    "No audio routing was changed.",
    "No PipeWire, WirePlumber, ALSA, service, system, or user audio configuration was modified.",
]


@dataclass(slots=True)
class BluetoothPolicyReport:
    passed: bool
    checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    bluetooth_available: bool | None = None
    devices_detected: list[str] = field(default_factory=list)
    active_profile: str = ""
    codec: str = ""
    hfp_hsp_suspected: bool = False
    a2dp_ok: bool = False
    collected_at: str = ""

    @property
    def verdict(self) -> str:
        if self.errors:
            return "fail"
        if self.warnings:
            return "warn"
        return "pass"


def run_bluetooth_policy_audit(
    wpctl_status: str | None = None,
    pactl_cards: str | None = None,
) -> BluetoothPolicyReport:
    checks: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []
    now = datetime.datetime.now(tz=datetime.timezone.utc).isoformat(timespec="seconds")

    if wpctl_status is None:
        ok, wpctl_status = collect_wpctl_status()
        if not ok:
            warnings.append(f"wpctl status unavailable: {wpctl_status}")
            wpctl_status = ""

    if pactl_cards is None:
        ok, pactl_cards = collect_pactl_cards()
        if not ok:
            pactl_cards = ""

    devices: list[str] = []
    has_bt = _has_bluetooth_device(wpctl_status, pactl_cards)

    if has_bt is None:
        warnings.append("Bluetooth device availability: unknown (wpctl/pactl not available)")
        bluetooth_available = None
    elif has_bt:
        bluetooth_available = True
        bt_names = _extract_bluetooth_device_names(wpctl_status, pactl_cards)
        devices.extend(bt_names)
        if bt_names:
            checks.append(f"Bluetooth device(s) detected: {', '.join(bt_names)}")
        else:
            checks.append("Bluetooth device detected (name unknown)")
    else:
        bluetooth_available = False
        checks.append("no Bluetooth audio devices detected")

    bt_profile_raw = _detect_bluetooth_profile(wpctl_status)
    active_profile = ""
    hfp_hsp_suspected = False
    a2dp_ok = False

    if bt_profile_raw == "hfp_hsp":
        active_profile = "HSP/HFP"
        hfp_hsp_suspected = True
        warnings.append(
            "Bluetooth device appears to be in HSP/HFP profile. "
            "HSP/HFP is designed for voice calls (8kHz or 16kHz codec). "
            "For music playback, A2DP is strongly preferred as it uses wideband stereo codecs. "
            "To switch: use a Bluetooth manager or pactl set-card-profile "
            "(PipeTune does not switch profiles automatically)."
        )
    elif bt_profile_raw == "a2dp":
        active_profile = "A2DP"
        a2dp_ok = True
        checks.append("Bluetooth profile: A2DP detected (preferred for music playback)")
    elif bt_profile_raw == "bluetooth_present":
        active_profile = "unknown"
        warnings.append(
            "Bluetooth device detected but profile is unknown or not parseable from wpctl output."
        )
    else:
        active_profile = ""

    codec = _detect_codec(wpctl_status, pactl_cards)
    if codec:
        checks.append(f"Bluetooth codec hint: {codec}")

    checks.append("bluetooth policy audit is read-only: no Bluetooth profile was changed")

    return BluetoothPolicyReport(
        passed=not errors,
        checks=checks,
        warnings=warnings,
        errors=errors,
        bluetooth_available=bluetooth_available,
        devices_detected=devices,
        active_profile=active_profile,
        codec=codec,
        hfp_hsp_suspected=hfp_hsp_suspected,
        a2dp_ok=a2dp_ok,
        collected_at=now,
    )


def render_bluetooth_policy_audit(report: BluetoothPolicyReport) -> str:
    lines = ["PipeTune Bluetooth Policy Audit", ""]
    lines.append("Checks:")
    for check in report.checks:
        lines.append(f"- pass: {check}")
    if not report.checks:
        lines.append("- none")
    if report.warnings:
        lines.append("")
        lines.append("Warnings:")
        for w in report.warnings:
            lines.append(f"- warn: {w}")
    if report.errors:
        lines.append("")
        lines.append("Errors:")
        for e in report.errors:
            lines.append(f"- fail: {e}")
    lines.append("")
    lines.append(f"Final verdict: {report.verdict}")
    lines.extend(_SAFETY_DISCLAIMER)
    return "\n".join(lines)


def render_bluetooth_policy_audit_json(report: BluetoothPolicyReport) -> str:
    return json.dumps(
        {
            "command": "bluetooth policy-audit",
            "pipetune_version": pipetune.__version__,
            "collected_at": report.collected_at,
            "host": _safe_hostname(),
            "verdict": report.verdict,
            "passed": report.passed,
            "checks": report.checks,
            "warnings": report.warnings,
            "errors": report.errors,
            "bluetooth_available": report.bluetooth_available,
            "devices_detected": report.devices_detected,
            "active_profile": report.active_profile,
            "codec": report.codec,
            "hfp_hsp_suspected": report.hfp_hsp_suspected,
            "a2dp_ok": report.a2dp_ok,
            "safety": {
                "read_only": True,
                "modified_system": False,
                "restarted_services": False,
                "changed_routing": False,
                "changed_bluetooth_profile": False,
            },
        },
        indent=2,
    )


def _has_bluetooth_device(wpctl_status: str, pactl_cards: str) -> bool | None:
    if not wpctl_status and not pactl_cards:
        return None
    combined = (wpctl_status + " " + pactl_cards).lower()
    return any(m.lower() in combined for m in _BLUETOOTH_DEVICE_MARKERS)


def _extract_bluetooth_device_names(wpctl_status: str, pactl_cards: str) -> list[str]:
    names: list[str] = []
    for line in wpctl_status.splitlines():
        stripped = line.strip()
        if any(m in stripped for m in _BLUETOOTH_DEVICE_MARKERS):
            parts = stripped.lstrip("*").strip().split(".")
            if len(parts) >= 2:
                name_part = ".".join(parts[1:]).split("[")[0].strip()
                if name_part:
                    names.append(name_part)
    return names


def _detect_codec(wpctl_status: str, pactl_cards: str) -> str:
    combined = wpctl_status + " " + pactl_cards
    for codec in _CODEC_HINTS:
        if codec in combined:
            return codec
    return ""


def _safe_hostname() -> str:
    try:
        return socket.gethostname()
    except OSError:
        return "unknown"
