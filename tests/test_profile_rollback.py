from __future__ import annotations

from pathlib import Path

from pipetune.activation.installer import install_profile
from pipetune.activation.manifest import list_install_manifests, load_install_manifest
from pipetune.activation.rollback import rollback_profile
from pipetune.safety.manifest import create_profile_manifest
from pipetune.safety.models import ActivationReadiness, HardwareQuirkMetadata, ProfilePreflightResult


def _preflight() -> ProfilePreflightResult:
    return ProfilePreflightResult(
        profile_name="Rollback",
        profile_type="headphone",
        config_path="rollback.filter-chain.conf",
        manifest_path="rollback.filter-chain.manifest.json",
        manifest_present=True,
        hardware_quirk=HardwareQuirkMetadata(False, "none", True, None, False, [], []),
        readiness=ActivationReadiness("ready", [], [], []),
    )


def _install(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("PIPETUNE_HOME", str(tmp_path / "home"))
    monkeypatch.setattr("pipetune.activation.installer.run_profile_preflight", lambda _config: _preflight())
    config = tmp_path / "rollback.filter-chain.conf"
    config.write_text(
        "# PipeTune Linux generated PipeWire filter-chain configuration\n# Preamp: -1 dB\ncontext.modules = [{ name = libpipewire-module-filter-chain args = { filter.graph = { nodes = [{ label = bq_peaking control = { \"Gain\" = 1 } }] } } }]\n",
        encoding="utf-8",
    )
    create_profile_manifest(config, "Rollback", "headphone")
    return install_profile(config, user_level=True, confirm_install=True, confirm_hardware_quirk=False)


def test_rollback_refuses_without_confirm_rollback(monkeypatch, tmp_path: Path) -> None:
    result = _install(monkeypatch, tmp_path)

    rollback = rollback_profile(install_id=result.install_id, confirm_rollback=False)

    assert rollback.success is False
    assert "Rollback requires --confirm-rollback." in rollback.errors


def test_rollback_latest_works_and_updates_manifest(monkeypatch, tmp_path: Path) -> None:
    result = _install(monkeypatch, tmp_path)

    rollback = rollback_profile(latest=True, confirm_rollback=True)

    assert rollback.success is True
    assert result.destination_path is not None
    assert not Path(result.destination_path).exists()
    manifest = load_install_manifest(list_install_manifests()[0][0])
    assert manifest is not None
    assert manifest.rollback_status == "rolled_back"
    assert rollback.rollback_log_path is not None and Path(rollback.rollback_log_path).exists()


def test_rollback_removes_only_manifest_owned_installed_config(monkeypatch, tmp_path: Path) -> None:
    result = _install(monkeypatch, tmp_path)
    unrelated = tmp_path / "home" / "config" / "pipewire" / "pipewire.conf.d" / "user.conf"
    unrelated.write_text("keep", encoding="utf-8")

    rollback = rollback_profile(install_id=result.install_id, confirm_rollback=True)

    assert rollback.success is True
    assert unrelated.exists()


def test_rollback_refuses_checksum_mismatch(monkeypatch, tmp_path: Path) -> None:
    result = _install(monkeypatch, tmp_path)
    assert result.destination_path is not None
    Path(result.destination_path).write_text("user modified", encoding="utf-8")

    rollback = rollback_profile(install_id=result.install_id, confirm_rollback=True)

    assert rollback.success is False
    assert "checksum mismatch" in rollback.errors[0]
