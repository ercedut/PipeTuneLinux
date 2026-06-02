from __future__ import annotations

from pathlib import Path

from pipetune.activation.installer import install_profile
from pipetune.activation.rollback import rollback_profile
from pipetune.activation.status import render_activation_status, render_installed_profiles
from pipetune.safety.manifest import create_profile_manifest
from pipetune.safety.models import ActivationReadiness, HardwareQuirkMetadata, ProfilePreflightResult


def _preflight() -> ProfilePreflightResult:
    return ProfilePreflightResult(
        profile_name="Status",
        profile_type="headphone",
        config_path="status.filter-chain.conf",
        manifest_path="status.filter-chain.manifest.json",
        manifest_present=True,
        hardware_quirk=HardwareQuirkMetadata(False, "none", True, None, False, [], []),
        readiness=ActivationReadiness("ready", [], [], []),
    )


def _install(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("PIPETUNE_HOME", str(tmp_path / "home"))
    monkeypatch.setattr("pipetune.activation.installer.run_profile_preflight", lambda _config: _preflight())
    monkeypatch.setattr(
        "pipetune.activation.status.collect_hardware_quirk_metadata",
        lambda: HardwareQuirkMetadata(False, "none", True, None, False, [], []),
    )
    config = tmp_path / "status.filter-chain.conf"
    config.write_text(
        "# PipeTune Linux generated PipeWire filter-chain configuration\n# Preamp: -1 dB\ncontext.modules = [{ name = libpipewire-module-filter-chain args = { filter.graph = { nodes = [{ label = bq_peaking control = { \"Gain\" = 1 } }] } } }]\n",
        encoding="utf-8",
    )
    create_profile_manifest(config, "Status", "headphone")
    return install_profile(config, user_level=True, confirm_install=True, confirm_hardware_quirk=False)


def test_list_installed_shows_no_profiles_when_empty(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PIPETUNE_HOME", str(tmp_path / "home"))

    output = render_installed_profiles()

    assert "No PipeTune-installed profiles found." in output


def test_list_installed_shows_active_profile(monkeypatch, tmp_path: Path) -> None:
    _install(monkeypatch, tmp_path)

    output = render_installed_profiles()

    assert "Install ID:" in output
    assert "Status: active" in output


def test_activation_status_reports_active_and_rolled_back_counts(monkeypatch, tmp_path: Path) -> None:
    _install(monkeypatch, tmp_path)
    rollback_profile(latest=True, confirm_rollback=True)

    output = render_activation_status()

    assert "Installed profiles: 1" in output
    assert "Active profiles: 0" in output
    assert "Rolled back profiles: 1" in output


def test_activation_status_reports_missing_installed_config_warning(monkeypatch, tmp_path: Path) -> None:
    result = _install(monkeypatch, tmp_path)
    assert result.destination_path is not None
    Path(result.destination_path).unlink()

    output = render_activation_status()

    assert "Manifest consistency: warn" in output
    assert "Installed config missing" in output
