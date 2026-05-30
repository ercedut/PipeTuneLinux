"""PipeWire collector."""

from __future__ import annotations

import re

from pipetune.collectors.command import run_command


def _parse_key_line(text: str, key: str) -> str | None:
    for line in text.splitlines():
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip() or None
    return None


def parse_pactl_default_name(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def _parse_wpctl_inspect_name(text: str) -> str | None:
    match = re.search(r'node\.name\s*=\s*"([^"]+)"', text)
    if match:
        return match.group(1).strip() or None

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("name:"):
            return stripped.split(":", 1)[1].strip() or None
    return None


def _parse_wpctl_status_default(text: str, route_kind: str) -> str | None:
    target_section = "Sinks:" if route_kind == "sink" else "Sources:"
    active_section = None

    for line in text.splitlines():
        stripped = line.strip()

        if stripped in {"Sinks:", "Sources:"}:
            active_section = stripped
            continue

        if stripped.endswith(":") and stripped not in {"Sinks:", "Sources:"}:
            active_section = None
            continue

        if active_section != target_section:
            continue

        if "*" not in stripped:
            continue

        # Try to extract node name from a wpctl status row such as:
        # * 52. alsa_output.pci-... [vol: 1.00]
        after_star = stripped.split("*", 1)[1].strip()
        if "." in after_star:
            maybe_id, remainder = after_star.split(".", 1)
            if maybe_id.strip().isdigit():
                candidate = remainder.strip()
            else:
                candidate = after_star
        else:
            candidate = after_star

        if " [" in candidate:
            candidate = candidate.split(" [", 1)[0].strip()
        if candidate:
            return candidate

    return None


def _is_explicit_missing_output(text: str, route_kind: str) -> bool:
    lowered = text.lower()
    if route_kind == "sink":
        phrases = ("no default sink", "default sink", "no such object", "not found")
    else:
        phrases = ("no default source", "default source", "no such object", "not found")
    return any(phrase in lowered for phrase in phrases)


def _route_object() -> dict:
    return {
        "detected": False,
        "name": None,
        "source": "unknown",
        "explicitly_missing": False,
    }


def collect_pipewire_data() -> dict:
    pipewire_status = run_command(["systemctl", "--user", "is-active", "pipewire"])
    pipewire_pulse_status = run_command(["systemctl", "--user", "is-active", "pipewire-pulse"])

    pactl_get_default_sink = run_command(["pactl", "get-default-sink"])
    pactl_get_default_source = run_command(["pactl", "get-default-source"])
    wpctl_inspect_default_sink = run_command(["wpctl", "inspect", "@DEFAULT_AUDIO_SINK@"]) 
    wpctl_inspect_default_source = run_command(["wpctl", "inspect", "@DEFAULT_AUDIO_SOURCE@"]) 

    wpctl_status = run_command(["wpctl", "status"])
    pactl_info = run_command(["pactl", "info"])
    pw_dump = run_command(["pw-dump"])

    pulse_server_name = None
    pulse_server_string = None
    if pactl_info.available and pactl_info.exit_code == 0:
        pulse_server_name = _parse_key_line(pactl_info.stdout, "Server Name")
        pulse_server_string = _parse_key_line(pactl_info.stdout, "Server String")

    default_sink = _route_object()
    default_source = _route_object()

    sink_name = None
    source_name = None

    if pactl_get_default_sink.available and pactl_get_default_sink.exit_code == 0:
        sink_name = parse_pactl_default_name(pactl_get_default_sink.stdout)
        if sink_name:
            default_sink = {"detected": True, "name": sink_name, "source": "pactl_get_default_sink", "explicitly_missing": False}
        else:
            default_sink["explicitly_missing"] = True
    elif pactl_get_default_sink.available:
        default_sink["explicitly_missing"] = _is_explicit_missing_output(
            f"{pactl_get_default_sink.stdout}\n{pactl_get_default_sink.stderr}", "sink"
        )

    if pactl_get_default_source.available and pactl_get_default_source.exit_code == 0:
        source_name = parse_pactl_default_name(pactl_get_default_source.stdout)
        if source_name:
            default_source = {
                "detected": True,
                "name": source_name,
                "source": "pactl_get_default_source",
                "explicitly_missing": False,
            }
        else:
            default_source["explicitly_missing"] = True
    elif pactl_get_default_source.available:
        default_source["explicitly_missing"] = _is_explicit_missing_output(
            f"{pactl_get_default_source.stdout}\n{pactl_get_default_source.stderr}", "source"
        )

    if not default_sink["detected"] and wpctl_inspect_default_sink.available and wpctl_inspect_default_sink.exit_code == 0:
        sink_name = _parse_wpctl_inspect_name(wpctl_inspect_default_sink.stdout)
        if sink_name:
            default_sink = {"detected": True, "name": sink_name, "source": "wpctl_inspect", "explicitly_missing": False}
        else:
            default_sink["explicitly_missing"] = True
    elif not default_sink["detected"] and wpctl_inspect_default_sink.available:
        default_sink["explicitly_missing"] = default_sink["explicitly_missing"] or _is_explicit_missing_output(
            f"{wpctl_inspect_default_sink.stdout}\n{wpctl_inspect_default_sink.stderr}", "sink"
        )

    if not default_source["detected"] and wpctl_inspect_default_source.available and wpctl_inspect_default_source.exit_code == 0:
        source_name = _parse_wpctl_inspect_name(wpctl_inspect_default_source.stdout)
        if source_name:
            default_source = {
                "detected": True,
                "name": source_name,
                "source": "wpctl_inspect",
                "explicitly_missing": False,
            }
        else:
            default_source["explicitly_missing"] = True
    elif not default_source["detected"] and wpctl_inspect_default_source.available:
        default_source["explicitly_missing"] = default_source["explicitly_missing"] or _is_explicit_missing_output(
            f"{wpctl_inspect_default_source.stdout}\n{wpctl_inspect_default_source.stderr}", "source"
        )

    if not default_sink["detected"] and wpctl_status.available and wpctl_status.exit_code == 0:
        sink_name = _parse_wpctl_status_default(wpctl_status.stdout, route_kind="sink")
        if sink_name:
            default_sink = {"detected": True, "name": sink_name, "source": "wpctl_status", "explicitly_missing": False}

    if not default_source["detected"] and wpctl_status.available and wpctl_status.exit_code == 0:
        source_name = _parse_wpctl_status_default(wpctl_status.stdout, route_kind="source")
        if source_name:
            default_source = {"detected": True, "name": source_name, "source": "wpctl_status", "explicitly_missing": False}

    if not default_sink["detected"] and pactl_info.available and pactl_info.exit_code == 0:
        sink_name = _parse_key_line(pactl_info.stdout, "Default Sink")
        if sink_name:
            default_sink = {"detected": True, "name": sink_name, "source": "pactl_info", "explicitly_missing": False}

    if not default_source["detected"] and pactl_info.available and pactl_info.exit_code == 0:
        source_name = _parse_key_line(pactl_info.stdout, "Default Source")
        if source_name:
            default_source = {"detected": True, "name": source_name, "source": "pactl_info", "explicitly_missing": False}

    filter_chain_detected = False
    if pw_dump.available and pw_dump.exit_code == 0:
        filter_chain_detected = "filter-chain" in pw_dump.stdout.lower()

    return {
        "services": {
            "pipewire": pipewire_status.to_dict(),
            "pipewire_pulse": pipewire_pulse_status.to_dict(),
        },
        "pactl_get_default_sink": pactl_get_default_sink.to_dict(),
        "pactl_get_default_source": pactl_get_default_source.to_dict(),
        "wpctl_inspect_default_sink": wpctl_inspect_default_sink.to_dict(),
        "wpctl_inspect_default_source": wpctl_inspect_default_source.to_dict(),
        "pactl_info": pactl_info.to_dict(),
        "wpctl_status": wpctl_status.to_dict(),
        "pw_dump": pw_dump.to_dict(),
        "default_sink": default_sink,
        "default_source": default_source,
        "pulse_server_name": pulse_server_name,
        "pulse_server_string": pulse_server_string,
        "filter_chain_detected": filter_chain_detected,
    }
