from __future__ import annotations

from pathlib import Path

from pipetune.activation.paths import backup_dir, install_state_dir, rollback_log_dir, user_pipewire_config_dir


def test_default_paths_are_user_level(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("PIPETUNE_HOME", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    assert user_pipewire_config_dir() == tmp_path / ".config" / "pipewire" / "pipewire.conf.d"
    assert install_state_dir() == tmp_path / ".local" / "share" / "pipetune" / "installed-profiles"
    assert backup_dir() == tmp_path / ".local" / "share" / "pipetune" / "backups"
    assert rollback_log_dir() == tmp_path / ".local" / "share" / "pipetune" / "rollback-log"


def test_pipetune_home_override_redirects_runtime_paths(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PIPETUNE_HOME", str(tmp_path))

    assert user_pipewire_config_dir() == tmp_path / "config" / "pipewire" / "pipewire.conf.d"
    assert install_state_dir() == tmp_path / "share" / "pipetune" / "installed-profiles"
    assert backup_dir() == tmp_path / "share" / "pipetune" / "backups"
    assert rollback_log_dir() == tmp_path / "share" / "pipetune" / "rollback-log"
