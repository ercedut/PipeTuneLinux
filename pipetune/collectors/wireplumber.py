"""WirePlumber collector."""

from __future__ import annotations

from pipetune.collectors.command import run_command


def collect_wireplumber_data() -> dict:
    wireplumber_status = run_command(["systemctl", "--user", "is-active", "wireplumber"])
    wpctl_status = run_command(["wpctl", "status"])

    has_managed_audio_nodes = False
    if wpctl_status.available and wpctl_status.exit_code == 0:
        out = wpctl_status.stdout
        has_managed_audio_nodes = ("Sinks:" in out) or ("Sources:" in out)

    return {
        "service_status": wireplumber_status.to_dict(),
        "wpctl_status": wpctl_status.to_dict(),
        "has_managed_audio_nodes": has_managed_audio_nodes,
    }
