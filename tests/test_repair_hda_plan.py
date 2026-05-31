from __future__ import annotations

from pathlib import Path

from pipetune.repair.hda_plan import build_repair_context, render_hda_plan


def test_hda_plan_output_contains_safety_and_rollback_language(tmp_path: Path) -> None:
    audit_dir = tmp_path / "audit"
    raw_dir = audit_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    (audit_dir / "README.md").write_text(
        "Speaker output currently works and must not be broken.\n"
        "Built-in microphone route is visible but not proven functional.\n",
        encoding="utf-8",
    )
    (audit_dir / "PUBLIC_SUMMARY.md").write_text(
        "- Manual HDA retask status: detected\n- Built-in mic route visibility: yes\n",
        encoding="utf-8",
    )
    (raw_dir / "hda-retask-search.txt").write_text(
        "/etc/modprobe.d/hda-jack-retask.conf:1:options snd-hda-intel model=generic\n",
        encoding="utf-8",
    )

    context = build_repair_context(audit_dir)
    output = render_hda_plan(context)

    assert "No system configuration was modified." in output
    assert "Do not break:" in output
    assert "- current speaker output" in output
    assert "Backup-first strategy:" in output
    assert "Rollback requirements:" in output
