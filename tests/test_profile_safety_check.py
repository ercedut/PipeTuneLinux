from __future__ import annotations

from pathlib import Path

from pipetune import cli


def test_profile_safety_check_command_exists() -> None:
    parser = cli._build_parser()
    args = parser.parse_args(["profile", "safety-check", "generated/test.filter-chain.conf"])

    assert args.command == "profile"
    assert args.profile_command == "safety-check"


def test_profile_preflight_command_exists() -> None:
    parser = cli._build_parser()
    args = parser.parse_args(["profile", "preflight", "generated/test.filter-chain.conf"])

    assert args.command == "profile"
    assert args.profile_command == "preflight"


def test_profile_safety_check_missing_file_returns_nonzero(tmp_path: Path) -> None:
    assert cli.main(["profile", "safety-check", str(tmp_path / "missing.conf")]) == 1
