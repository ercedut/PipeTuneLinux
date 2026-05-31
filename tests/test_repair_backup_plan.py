from __future__ import annotations

from pathlib import Path

from pipetune.repair.backup_plan import render_backup_plan


def test_backup_plan_marks_commands_manual(tmp_path: Path) -> None:
    audit_dir = tmp_path / "audit"
    raw_dir = audit_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "hda-retask-search.txt").write_text(
        "/etc/modprobe.d/custom-hda.conf:3:options snd-hda-intel model=generic\n",
        encoding="utf-8",
    )

    output = render_backup_plan(audit_dir)

    assert "MANUAL / DO NOT RUN BLINDLY" in output
    assert "/etc/modprobe.d/hda-jack-retask.conf" in output
    assert "/lib/firmware/hda-jack-retask.fw" in output
    assert "/etc/modprobe.d/custom-hda.conf" in output
    assert "No system configuration was modified." in output
