"""Hardware quirk audit tools."""

from pipetune.hardware.hda_audit import collect_hda_audit, render_hda_audit_summary
from pipetune.hardware.mic_audit import collect_mic_audit, render_mic_audit_summary
from pipetune.hardware.quirk_report import create_quirk_report

__all__ = [
    "collect_hda_audit",
    "render_hda_audit_summary",
    "collect_mic_audit",
    "render_mic_audit_summary",
    "create_quirk_report",
]
