from __future__ import annotations

from pathlib import Path

from pipetune.hardware.hda_audit import _search_retask_references, collect_hda_audit


def _mock_alsa_data() -> dict:
    return {
        "capture_devices": ["card 0: PCH [HDA], device 0: ALC mic"],
        "cards": ["0 [PCH]"],
        "ucm2_directory": {"exists": True},
    }


def test_detects_non_empty_user_pin_configs_as_manual_retask(monkeypatch, tmp_path: Path) -> None:
    proc = tmp_path / "proc_asound"
    sys_class = tmp_path / "sys_class_sound"
    modprobe = tmp_path / "modprobe"
    firmware = tmp_path / "firmware"

    (proc / "cards").parent.mkdir(parents=True, exist_ok=True)
    (proc / "cards").write_text("0 [PCH ]: HDA\n", encoding="utf-8")
    (proc / "card0").mkdir(parents=True, exist_ok=True)
    (proc / "card0" / "codec#0").write_text("Codec: Realtek", encoding="utf-8")

    pin_file = sys_class / "hwC0D0" / "device" / "user_pin_configs"
    pin_file.parent.mkdir(parents=True, exist_ok=True)
    pin_file.write_text("0x17 0x40000000\n", encoding="utf-8")

    modprobe.mkdir(parents=True, exist_ok=True)
    firmware.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("pipetune.hardware.hda_audit.collect_alsa_data", _mock_alsa_data)

    result = collect_hda_audit(
        proc_asound_dir=proc,
        sys_class_sound_dir=sys_class,
        modprobe_dir=modprobe,
        firmware_dir=firmware,
        historical_routing_issue_noted=True,
    )

    assert result.manual_hda_retask_detected is True
    assert result.manual_hda_retask_suspected is False


def test_detects_hda_jack_retask_text_in_modprobe_search_result(monkeypatch, tmp_path: Path) -> None:
    proc = tmp_path / "proc_asound"
    sys_class = tmp_path / "sys_class_sound"
    modprobe = tmp_path / "modprobe"
    firmware = tmp_path / "firmware"

    (proc / "cards").parent.mkdir(parents=True, exist_ok=True)
    (proc / "cards").write_text("0 [PCH ]: HDA\n", encoding="utf-8")
    (proc / "card0").mkdir(parents=True, exist_ok=True)
    (proc / "card0" / "codec#0").write_text("Codec: Realtek", encoding="utf-8")

    modprobe.mkdir(parents=True, exist_ok=True)
    (modprobe / "hda-jack-retask.conf").write_text("options snd-hda-intel model=generic\n", encoding="utf-8")
    firmware.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("pipetune.hardware.hda_audit.collect_alsa_data", _mock_alsa_data)

    result = collect_hda_audit(
        proc_asound_dir=proc,
        sys_class_sound_dir=sys_class,
        modprobe_dir=modprobe,
        firmware_dir=firmware,
        historical_routing_issue_noted=True,
    )

    assert result.manual_hda_retask_detected is True
    assert any("hda-jack-retask" in line or "model=" in line for line in result.retask_reference_hits)


def test_missing_hda_files_does_not_crash(monkeypatch, tmp_path: Path) -> None:
    proc = tmp_path / "proc_asound"
    sys_class = tmp_path / "sys_class_sound"
    modprobe = tmp_path / "modprobe"
    firmware = tmp_path / "firmware"
    proc.mkdir(parents=True, exist_ok=True)
    sys_class.mkdir(parents=True, exist_ok=True)
    modprobe.mkdir(parents=True, exist_ok=True)
    firmware.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("pipetune.hardware.hda_audit.collect_alsa_data", _mock_alsa_data)

    result = collect_hda_audit(
        proc_asound_dir=proc,
        sys_class_sound_dir=sys_class,
        modprobe_dir=modprobe,
        firmware_dir=firmware,
        historical_routing_issue_noted=True,
    )

    assert result.codec_files == []
    assert result.manual_hda_retask_detected is False
    assert all("command not found: rg" not in warning for warning in result.warnings)


def test_codec_files_present_are_reported(monkeypatch, tmp_path: Path) -> None:
    proc = tmp_path / "proc_asound"
    sys_class = tmp_path / "sys_class_sound"
    modprobe = tmp_path / "modprobe"
    firmware = tmp_path / "firmware"

    (proc / "card0").mkdir(parents=True, exist_ok=True)
    codec_path = proc / "card0" / "codec#0"
    codec_path.write_text("Codec: Realtek", encoding="utf-8")
    (proc / "cards").write_text("0 [PCH ]: HDA\n", encoding="utf-8")

    sys_class.mkdir(parents=True, exist_ok=True)
    modprobe.mkdir(parents=True, exist_ok=True)
    firmware.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("pipetune.hardware.hda_audit.collect_alsa_data", _mock_alsa_data)

    result = collect_hda_audit(
        proc_asound_dir=proc,
        sys_class_sound_dir=sys_class,
        modprobe_dir=modprobe,
        firmware_dir=firmware,
        historical_routing_issue_noted=True,
    )

    assert str(codec_path) in result.codec_files


def test_retask_search_works_without_rg(monkeypatch, tmp_path: Path) -> None:
    modprobe = tmp_path / "modprobe"
    modprobe.mkdir(parents=True, exist_ok=True)
    target = modprobe / "hda-jack-retask.conf"
    target.write_text("options snd-hda-intel model=generic\n", encoding="utf-8")

    # Ensure search implementation does not shell out.
    monkeypatch.setattr("pipetune.hardware.hda_audit.run_command", lambda *args, **kwargs: None, raising=False)

    hits, warnings, scanned, skipped = _search_retask_references(modprobe)

    assert warnings == []
    assert any("model=generic" in hit for hit in hits)
    assert scanned >= 1
    assert skipped >= 0


def test_missing_search_directories_do_not_crash(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    hits, warnings, scanned, skipped = _search_retask_references(missing)

    assert hits == []
    assert any("missing" in warning for warning in warnings)
    assert scanned == 0


def test_unreadable_files_are_skipped_safely(tmp_path: Path, monkeypatch) -> None:
    modprobe = tmp_path / "modprobe"
    modprobe.mkdir(parents=True, exist_ok=True)
    target = modprobe / "blocked.conf"
    target.write_text("hda-jack-retask\n", encoding="utf-8")

    original_read_text = Path.read_text

    def fake_read_text(self: Path, *args, **kwargs):
        if self == target:
            raise PermissionError("denied")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fake_read_text)

    hits, warnings, scanned, skipped = _search_retask_references(modprobe)

    assert hits == []
    assert warnings == []
    assert scanned == 0
    assert skipped >= 1


def test_large_files_are_skipped(tmp_path: Path) -> None:
    modprobe = tmp_path / "modprobe"
    modprobe.mkdir(parents=True, exist_ok=True)
    large_file = modprobe / "hda-jack-retask.conf"
    large_file.write_text("x" * (1_000_001), encoding="utf-8")

    hits, warnings, scanned, skipped = _search_retask_references(modprobe)

    assert hits == []
    assert warnings == []
    assert scanned == 0
    assert skipped >= 1


def test_binary_like_files_are_skipped(tmp_path: Path) -> None:
    firmware = tmp_path / "firmware"
    firmware.mkdir(parents=True, exist_ok=True)
    binary_file = firmware / "hda-jack-retask.fw"
    binary_file.write_bytes(b"\x00\x01\x02hda-jack-retask\x03")

    hits, warnings, scanned, skipped = _search_retask_references(firmware)

    assert hits == []
    assert warnings == []
    assert scanned == 0
    assert skipped >= 1


def test_max_file_limit_stops_scanning(tmp_path: Path) -> None:
    modprobe = tmp_path / "modprobe"
    modprobe.mkdir(parents=True, exist_ok=True)
    for index in range(10):
        (modprobe / f"config-{index}.conf").write_text("no match\n", encoding="utf-8")

    hits, warnings, scanned, skipped = _search_retask_references(modprobe, max_scanned_files=3)

    assert hits == []
    assert scanned <= 3
    assert any("file scan limit" in warning for warning in warnings)
    assert skipped >= 0
