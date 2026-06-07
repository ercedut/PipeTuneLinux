"""WirePlumber install-guide — safe step-by-step workflow for users.

Read-only.  No files created.  No services restarted.  No routing changed.
"""
from __future__ import annotations

import json

_GUIDE_STEPS = [
    "1. Run a route audit to understand current routing:",
    "   pipetune route audit",
    "2. If Bluetooth is involved, run Bluetooth policy audit:",
    "   pipetune bluetooth policy-audit",
    "3. Generate a WirePlumber rule preview (read-only, NOT installed):",
    "   pipetune wireplumber suggest-rule --dry-run --user-only",
    "4. Validate the generated preview:",
    "   pipetune wireplumber validate-preview <preview_file>",
    "5. Run install preflight to verify your environment is ready:",
    "   pipetune wireplumber install-preflight",
    "6. Dry-run the install to see what would happen without writing anything:",
    "   pipetune wireplumber install-rule <preview_file> --user-only --dry-run",
    "7. Only if you accept the dry-run output, confirm the install:",
    "   pipetune wireplumber install-rule <preview_file> --user-only --confirm-install",
    "8. Review the installed rule file manually before activating.",
    "9. If desired, manually reload/restart WirePlumber OUTSIDE PipeTune.",
    "   PipeTune does NOT restart services.",
    "10. If the rule is not working or you wish to undo it:",
    "    pipetune wireplumber rollback-rule <install_id> --dry-run",
    "    pipetune wireplumber rollback-rule <install_id> --confirm-rollback",
]

_GUIDE_SAFETY_NOTES = [
    "PipeTune does NOT restart services.",
    "PipeTune does NOT route audio.",
    "PipeTune does NOT switch Bluetooth profiles.",
    "All installs are user-level only (XDG_CONFIG_HOME/wireplumber/wireplumber.conf.d).",
    "Always run --dry-run first before --confirm-install.",
    "Use rollback-rule to undo any PipeTune-installed rule.",
    "Manually reload/restart WirePlumber outside PipeTune if you want a rule to take effect.",
]

_GUIDE_SAFETY_LINES = [
    "This command is read-only.",
    "No service was restarted.",
    "No audio routing was changed.",
    "No PipeWire, WirePlumber, ALSA, service, system, or user audio configuration was modified.",
]


def render_install_guide() -> str:
    lines = ["PipeTune WirePlumber Install Guide", ""]
    lines.append("Safe step-by-step workflow for WirePlumber rule installation:")
    lines.append("")
    lines.extend(_GUIDE_STEPS)
    lines.extend(["", "Safety notes:"])
    lines.extend(f"* {note}" for note in _GUIDE_SAFETY_NOTES)
    lines.extend(["", *_GUIDE_SAFETY_LINES])
    return "\n".join(lines)


def render_install_guide_json() -> str:
    payload = {
        "command": "wireplumber install-guide",
        "steps": _GUIDE_STEPS,
        "safety_notes": _GUIDE_SAFETY_NOTES,
        "safety": {
            "read_only": True,
            "wrote_files": False,
            "restarted_services": False,
            "changed_routing": False,
            "modified_system": False,
        },
    }
    return json.dumps(payload, indent=2, sort_keys=True)
