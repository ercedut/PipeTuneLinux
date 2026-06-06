"""Diagnostic logic for WirePlumber and routing analysis."""

from __future__ import annotations

import datetime
import re
import socket

from pipetune.wireplumber.collect import (
    collect_pactl_cards,
    collect_pactl_info,
    collect_pactl_sinks,
    collect_pactl_sources,
    collect_service_status,
    collect_wpctl_status,
)
from pipetune.wireplumber.models import (
    RouteAuditReport,
    ServiceStatus,
    WirePlumberAuditReport,
)

_PIPETUNE_FILTER_CHAIN_MARKER = "pipetune"
_VIRTUAL_SINK_MARKERS = ("filter-chain", "virtual", "pipetune")
_HFP_HSP_MARKERS = ("HSP/HFP", "hfp", "hsp", "HSP", "HFP", "headset", "Headset")
_A2DP_MARKERS = ("A2DP", "a2dp", "Advanced Audio", "advanced-audio")
_BLUETOOTH_MARKERS = ("bluez", "bluetooth", "Bluetooth", "BlueTooth")


def run_wireplumber_audit(
    wpctl_status: str | None = None,
    pactl_info: str | None = None,
    pactl_sinks: str | None = None,
    pactl_sources: str | None = None,
    pactl_cards: str | None = None,
    service_statuses: dict[str, tuple[bool | None, str]] | None = None,
) -> WirePlumberAuditReport:
    checks: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []

    now = datetime.datetime.now(tz=datetime.timezone.utc).isoformat(timespec="seconds")

    if service_statuses is None:
        service_statuses = {}
        for svc in ("wireplumber", "pipewire", "pipewire-pulse"):
            active, details = collect_service_status(svc)
            service_statuses[svc] = (active, details)

    services: list[ServiceStatus] = []
    for svc_name, (active, details) in service_statuses.items():
        svc = ServiceStatus(name=svc_name, active=active, details=details)
        services.append(svc)
        if active is True:
            checks.append(f"{svc_name}: active")
        elif active is False:
            warnings.append(f"{svc_name}: inactive or not running ({details})")
        else:
            warnings.append(f"{svc_name}: status unknown ({details})")

    if wpctl_status is None:
        ok, wpctl_status = collect_wpctl_status()
        if not ok:
            warnings.append(f"wpctl status unavailable: {wpctl_status}")
            wpctl_status = ""

    if pactl_info is None:
        ok, pactl_info = collect_pactl_info()
        if not ok:
            warnings.append(f"pactl info unavailable: {pactl_info}")
            pactl_info = ""

    if pactl_sinks is None:
        ok, pactl_sinks = collect_pactl_sinks()
        if not ok:
            pactl_sinks = ""

    if pactl_sources is None:
        ok, pactl_sources = collect_pactl_sources()
        if not ok:
            pactl_sources = ""

    if pactl_cards is None:
        ok, pactl_cards = collect_pactl_cards()
        if not ok:
            pactl_cards = ""

    default_sink = _parse_default_sink(pactl_info)
    default_source = _parse_default_source(pactl_info)

    if default_sink:
        checks.append(f"default sink: {default_sink}")
    else:
        warnings.append("default sink: not detected or unknown")

    if default_source:
        checks.append(f"default source: {default_source}")
    else:
        warnings.append("default source: not detected or unknown")

    sink_count = _count_sink_blocks(pactl_sinks)
    source_count = _count_source_blocks(pactl_sources)
    card_count = _count_card_blocks(pactl_cards)

    checks.append(f"detected sinks: {sink_count}")
    checks.append(f"detected sources: {source_count}")
    checks.append(f"detected cards: {card_count}")

    bt_profile = _detect_bluetooth_profile(wpctl_status)
    if bt_profile == "hfp_hsp":
        warnings.append(
            "Bluetooth device detected in HSP/HFP profile; "
            "HFP/HSP is optimized for voice calls, not music. "
            "A2DP is usually preferred for music playback."
        )
    elif bt_profile == "a2dp":
        checks.append("Bluetooth device: A2DP profile (preferred for music playback)")
    elif bt_profile == "bluetooth_present":
        warnings.append("Bluetooth device detected; profile unknown or not parseable")

    checks.append("wireplumber audit is read-only: no routing changed, no config modified")

    passed = not errors
    return WirePlumberAuditReport(
        passed=passed,
        checks=checks,
        warnings=warnings,
        errors=errors,
        services=services,
        default_sink=default_sink,
        default_source=default_source,
        sink_count=sink_count,
        source_count=source_count,
        card_count=card_count,
        collected_at=now,
    )


def run_route_audit(
    pactl_info: str | None = None,
    pactl_sinks: str | None = None,
    pactl_sources: str | None = None,
    wpctl_status: str | None = None,
) -> RouteAuditReport:
    checks: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []

    now = datetime.datetime.now(tz=datetime.timezone.utc).isoformat(timespec="seconds")

    if pactl_info is None:
        ok, pactl_info = collect_pactl_info()
        if not ok:
            warnings.append(f"pactl info unavailable: {pactl_info}")
            pactl_info = ""

    if pactl_sinks is None:
        ok, pactl_sinks = collect_pactl_sinks()
        if not ok:
            pactl_sinks = ""

    if pactl_sources is None:
        ok, pactl_sources = collect_pactl_sources()
        if not ok:
            pactl_sources = ""

    if wpctl_status is None:
        ok, wpctl_status = collect_wpctl_status()
        if not ok:
            wpctl_status = ""

    default_sink = _parse_default_sink(pactl_info)
    default_source = _parse_default_source(pactl_info)

    if default_sink:
        checks.append(f"default output route: {default_sink}")
    else:
        warnings.append("default output route: not detected")

    if default_source:
        checks.append(f"default input route: {default_source}")
    else:
        warnings.append("default input route: not detected")

    sink_count = _count_sink_blocks(pactl_sinks)
    source_count = _count_source_blocks(pactl_sources)
    checks.append(f"sinks detected: {sink_count}")
    checks.append(f"sources detected: {source_count}")

    if sink_count == 0:
        errors.append("no audio sinks detected; output routing may be broken")
    elif default_sink and not _default_exists_in_sinks(default_sink, pactl_sinks):
        warnings.append(
            f"default sink '{default_sink}' was not found in detected sink list"
        )

    has_virtual = _detect_virtual_sinks(pactl_sinks)
    has_pipetune = _detect_pipetune_configs(pactl_sinks, wpctl_status)
    bt_profile = _detect_bluetooth_profile(wpctl_status)

    if has_virtual:
        checks.append("virtual filter-chain sink(s) detected in sink list")
    else:
        checks.append("no virtual filter-chain sinks detected")

    if has_pipetune:
        checks.append("PipeTune-related filter-chain config appears active")
    else:
        checks.append("no PipeTune filter-chain config detected as active")

    if bt_profile == "hfp_hsp":
        warnings.append(
            "Bluetooth default route in HSP/HFP profile: "
            "HFP/HSP is intended for voice calls, not music. "
            "A2DP typically provides better audio quality for music playback."
        )
    elif bt_profile == "a2dp":
        checks.append("Bluetooth route: A2DP profile (good for music playback)")

    checks.append("route audit is read-only: no routing changed, no config modified")

    passed = not errors
    return RouteAuditReport(
        passed=passed,
        checks=checks,
        warnings=warnings,
        errors=errors,
        default_sink=default_sink,
        default_source=default_source,
        sink_count=sink_count,
        source_count=source_count,
        has_virtual_sinks=has_virtual,
        has_pipetune_configs=has_pipetune,
        bluetooth_hfp_suspected=(bt_profile == "hfp_hsp"),
        collected_at=now,
    )


def build_route_explain_text() -> list[str]:
    return [
        "PipeWire Routing Explanation",
        "",
        "Signal path:",
        "  App/browser → pipewire-pulse → PipeWire graph → WirePlumber policy → ALSA/Bluetooth device",
        "",
        "Key concepts:",
        "",
        "  Default sink:",
        "    The audio output device that PipeWire routes playback to by default.",
        "    Applications that do not request a specific device will use this sink.",
        "    Change with: wpctl set-default <id>  (not done automatically by PipeTune)",
        "",
        "  Default source:",
        "    The audio input device that PipeWire routes recording from by default.",
        "    Microphone capture typically uses this unless explicitly overridden.",
        "",
        "  WirePlumber:",
        "    The session and policy manager for PipeWire.",
        "    It decides which device is default, how Bluetooth profiles are selected,",
        "    and how virtual devices (filter-chains) are connected.",
        "",
        "  pipewire-pulse:",
        "    A PulseAudio-compatibility layer inside PipeWire.",
        "    Applications that use the PulseAudio API are served through this layer.",
        "",
        "  Virtual filter-chain sinks:",
        "    Software sinks that process audio before sending it to a real device.",
        "    PipeTune-generated filter-chain configs create these when installed.",
        "    They appear as extra sinks in pactl/wpctl output.",
        "",
        "  Bluetooth profile — why it matters:",
        "    HSP/HFP (Headset/Hands-Free Profile): designed for voice calls.",
        "      Uses a narrow 8kHz or 16kHz codec, which sounds poor for music.",
        "    A2DP (Advanced Audio Distribution Profile): designed for music.",
        "      Uses a wideband stereo codec (SBC, AAC, aptX, LDAC).",
        "    If a Bluetooth device is in HSP/HFP mode, music quality will be degraded.",
        "    Switching to A2DP is typically done through WirePlumber policy or",
        "    manually via pactl set-card-profile — PipeTune does not do this automatically.",
        "",
        "Why this command is read-only:",
        "  PipeTune only observes the current routing state.",
        "  It does not call wpctl set-default, pactl set-card-profile, or modify",
        "  any WirePlumber, PipeWire, ALSA, or user audio configuration.",
        "  All changes to routing require explicit user action.",
        "",
        "No system configuration was modified.",
        "No audio routing was changed.",
        "No PipeWire, WirePlumber, ALSA, service, system, or user audio configuration was modified.",
    ]


def _parse_default_sink(pactl_info: str) -> str:
    for line in pactl_info.splitlines():
        if line.strip().startswith("Default Sink:"):
            return line.split(":", 1)[1].strip()
    return ""


def _parse_default_source(pactl_info: str) -> str:
    for line in pactl_info.splitlines():
        if line.strip().startswith("Default Source:"):
            return line.split(":", 1)[1].strip()
    return ""


def _count_sink_blocks(pactl_sinks: str) -> int:
    return len(re.findall(r"^Sink #", pactl_sinks, re.MULTILINE))


def _count_source_blocks(pactl_sources: str) -> int:
    return len(re.findall(r"^Source #", pactl_sources, re.MULTILINE))


def _count_card_blocks(pactl_cards: str) -> int:
    return len(re.findall(r"^Card #", pactl_cards, re.MULTILINE))


def _detect_bluetooth_profile(wpctl_status: str) -> str:
    if not wpctl_status:
        return ""
    for marker in _HFP_HSP_MARKERS:
        if marker in wpctl_status:
            return "hfp_hsp"
    for marker in _A2DP_MARKERS:
        if marker in wpctl_status:
            return "a2dp"
    for marker in _BLUETOOTH_MARKERS:
        if marker in wpctl_status:
            return "bluetooth_present"
    return ""


def _detect_virtual_sinks(pactl_sinks: str) -> bool:
    if not pactl_sinks:
        return False
    lower = pactl_sinks.lower()
    return any(marker in lower for marker in _VIRTUAL_SINK_MARKERS)


def _detect_pipetune_configs(pactl_sinks: str, wpctl_status: str) -> bool:
    combined = (pactl_sinks + " " + wpctl_status).lower()
    return _PIPETUNE_FILTER_CHAIN_MARKER in combined


def _default_exists_in_sinks(default_sink: str, pactl_sinks: str) -> bool:
    if not default_sink or not pactl_sinks:
        return True  # cannot verify — assume ok
    return default_sink.lower() in pactl_sinks.lower()
