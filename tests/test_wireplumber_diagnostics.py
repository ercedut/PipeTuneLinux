"""Tests for v0.8.0 WirePlumber and routing diagnostics."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

import pipetune
from pipetune import cli
from pipetune.wireplumber import diagnose, render
from pipetune.wireplumber.models import RouteAuditReport, WirePlumberAuditReport


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "wireplumber"


def _load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Version check
# ---------------------------------------------------------------------------


def test_version_is_080() -> None:
    assert pipetune.__version__ == "0.8.1"


def test_version_codename_wireplumber() -> None:
    assert "WirePlumber" in pipetune.CODENAME or "Routing" in pipetune.CODENAME


# ---------------------------------------------------------------------------
# Fixture files exist
# ---------------------------------------------------------------------------


def test_fixture_wpctl_status_basic_exists() -> None:
    assert (FIXTURES / "wpctl-status-basic.txt").exists()


def test_fixture_wpctl_status_bluetooth_hfp_exists() -> None:
    assert (FIXTURES / "wpctl-status-bluetooth-hfp.txt").exists()


def test_fixture_pactl_info_basic_exists() -> None:
    assert (FIXTURES / "pactl-info-basic.txt").exists()


def test_fixture_pactl_cards_basic_exists() -> None:
    assert (FIXTURES / "pactl-cards-basic.txt").exists()


def test_fixture_pactl_sinks_basic_exists() -> None:
    assert (FIXTURES / "pactl-sinks-basic.txt").exists()


def test_fixture_pactl_sources_basic_exists() -> None:
    assert (FIXTURES / "pactl-sources-basic.txt").exists()


def test_fixture_pw_dump_minimal_exists() -> None:
    assert (FIXTURES / "pw-dump-minimal.json").exists()


# ---------------------------------------------------------------------------
# WirePlumber audit — parsing fixture data
# ---------------------------------------------------------------------------


def _make_service_statuses(wp=True, pw=True, pwp=True):
    return {
        "wireplumber": (wp, "active" if wp else "inactive"),
        "pipewire": (pw, "active" if pw else "inactive"),
        "pipewire-pulse": (pwp, "active" if pwp else "inactive"),
    }


def test_wireplumber_audit_all_services_active():
    pactl_info = _load_fixture("pactl-info-basic.txt")
    pactl_sinks = _load_fixture("pactl-sinks-basic.txt")
    pactl_sources = _load_fixture("pactl-sources-basic.txt")
    pactl_cards = _load_fixture("pactl-cards-basic.txt")
    wpctl_status = _load_fixture("wpctl-status-basic.txt")

    report = diagnose.run_wireplumber_audit(
        wpctl_status=wpctl_status,
        pactl_info=pactl_info,
        pactl_sinks=pactl_sinks,
        pactl_sources=pactl_sources,
        pactl_cards=pactl_cards,
        service_statuses=_make_service_statuses(),
    )
    assert report.passed
    assert report.verdict == "pass"
    service_checks = [c for c in report.checks if "wireplumber: active" in c or "pipewire: active" in c or "pipewire-pulse: active" in c]
    assert len(service_checks) == 3


def test_wireplumber_audit_detects_default_sink():
    pactl_info = _load_fixture("pactl-info-basic.txt")
    report = diagnose.run_wireplumber_audit(
        wpctl_status="",
        pactl_info=pactl_info,
        pactl_sinks="",
        pactl_sources="",
        pactl_cards="",
        service_statuses=_make_service_statuses(),
    )
    assert report.default_sink == "alsa_output.pci-0000_00_1f.3.analog-stereo"
    assert any("default sink" in c for c in report.checks)


def test_wireplumber_audit_detects_default_source():
    pactl_info = _load_fixture("pactl-info-basic.txt")
    report = diagnose.run_wireplumber_audit(
        wpctl_status="",
        pactl_info=pactl_info,
        pactl_sinks="",
        pactl_sources="",
        pactl_cards="",
        service_statuses=_make_service_statuses(),
    )
    assert report.default_source == "alsa_input.pci-0000_00_1f.3.analog-stereo"


def test_wireplumber_audit_sink_count():
    pactl_sinks = _load_fixture("pactl-sinks-basic.txt")
    report = diagnose.run_wireplumber_audit(
        wpctl_status="",
        pactl_info="",
        pactl_sinks=pactl_sinks,
        pactl_sources="",
        pactl_cards="",
        service_statuses=_make_service_statuses(),
    )
    assert report.sink_count == 1


def test_wireplumber_audit_card_count():
    pactl_cards = _load_fixture("pactl-cards-basic.txt")
    report = diagnose.run_wireplumber_audit(
        wpctl_status="",
        pactl_info="",
        pactl_sinks="",
        pactl_sources="",
        pactl_cards=pactl_cards,
        service_statuses=_make_service_statuses(),
    )
    assert report.card_count == 1


def test_wireplumber_audit_inactive_service_warns():
    report = diagnose.run_wireplumber_audit(
        wpctl_status="",
        pactl_info="",
        pactl_sinks="",
        pactl_sources="",
        pactl_cards="",
        service_statuses={"wireplumber": (False, "inactive"), "pipewire": (True, "active"), "pipewire-pulse": (True, "active")},
    )
    assert any("wireplumber" in w and "inactive" in w for w in report.warnings)


def test_wireplumber_audit_unknown_service_warns():
    report = diagnose.run_wireplumber_audit(
        wpctl_status="",
        pactl_info="",
        pactl_sinks="",
        pactl_sources="",
        pactl_cards="",
        service_statuses={"wireplumber": (None, "unknown"), "pipewire": (True, "active"), "pipewire-pulse": (True, "active")},
    )
    assert any("wireplumber" in w and "unknown" in w for w in report.warnings)


def test_wireplumber_audit_no_default_sink_warns():
    report = diagnose.run_wireplumber_audit(
        wpctl_status="",
        pactl_info="Server String: /run/user/1000/pulse/native\n",
        pactl_sinks="",
        pactl_sources="",
        pactl_cards="",
        service_statuses=_make_service_statuses(),
    )
    assert any("default sink" in w for w in report.warnings)


def test_wireplumber_audit_bluetooth_hfp_warns():
    wpctl_status = _load_fixture("wpctl-status-bluetooth-hfp.txt")
    report = diagnose.run_wireplumber_audit(
        wpctl_status=wpctl_status,
        pactl_info="",
        pactl_sinks="",
        pactl_sources="",
        pactl_cards="",
        service_statuses=_make_service_statuses(),
    )
    assert any("HSP/HFP" in w or "HFP" in w or "hfp" in w.lower() for w in report.warnings)


def test_wireplumber_audit_a2dp_ok():
    wpctl_status = "* 61. My Headphones (A2DP Sink)  [vol: 0.80]\n"
    report = diagnose.run_wireplumber_audit(
        wpctl_status=wpctl_status,
        pactl_info="",
        pactl_sinks="",
        pactl_sources="",
        pactl_cards="",
        service_statuses=_make_service_statuses(),
    )
    assert any("A2DP" in c for c in report.checks)


def test_wireplumber_audit_is_readonly():
    report = diagnose.run_wireplumber_audit(
        wpctl_status="",
        pactl_info="",
        pactl_sinks="",
        pactl_sources="",
        pactl_cards="",
        service_statuses=_make_service_statuses(),
    )
    assert any("read-only" in c for c in report.checks)


def test_wireplumber_audit_malformed_pactl_info():
    report = diagnose.run_wireplumber_audit(
        wpctl_status="",
        pactl_info="GARBAGE DATA\nno keys here\n",
        pactl_sinks="",
        pactl_sources="",
        pactl_cards="",
        service_statuses=_make_service_statuses(),
    )
    assert any("default sink" in w for w in report.warnings)
    assert any("default source" in w for w in report.warnings)


# ---------------------------------------------------------------------------
# Route audit — fixture parsing
# ---------------------------------------------------------------------------


def test_route_audit_basic():
    pactl_info = _load_fixture("pactl-info-basic.txt")
    pactl_sinks = _load_fixture("pactl-sinks-basic.txt")
    pactl_sources = _load_fixture("pactl-sources-basic.txt")
    wpctl_status = _load_fixture("wpctl-status-basic.txt")

    report = diagnose.run_route_audit(
        pactl_info=pactl_info,
        pactl_sinks=pactl_sinks,
        pactl_sources=pactl_sources,
        wpctl_status=wpctl_status,
    )
    assert report.default_sink == "alsa_output.pci-0000_00_1f.3.analog-stereo"
    assert report.sink_count == 1
    assert any("default output route" in c for c in report.checks)


def test_route_audit_no_sinks_is_error():
    report = diagnose.run_route_audit(
        pactl_info="",
        pactl_sinks="",
        pactl_sources="",
        wpctl_status="",
    )
    assert any("no audio sinks" in e or "sinks detected" in e for e in report.errors)


def test_route_audit_bluetooth_hfp_warns():
    wpctl_status = _load_fixture("wpctl-status-bluetooth-hfp.txt")
    report = diagnose.run_route_audit(
        pactl_info="",
        pactl_sinks="",
        pactl_sources="",
        wpctl_status=wpctl_status,
    )
    assert report.bluetooth_hfp_suspected
    assert any("HFP" in w or "hfp" in w.lower() for w in report.warnings)


def test_route_audit_a2dp_ok():
    wpctl_status = "* 61. My Headphones (A2DP Sink)  [vol: 0.80]\n"
    pactl_sinks = "Sink #1\n\tName: a2dp_sink\n\tDescription: My Headphones A2DP\n"
    report = diagnose.run_route_audit(
        pactl_info="",
        pactl_sinks=pactl_sinks,
        pactl_sources="",
        wpctl_status=wpctl_status,
    )
    assert not report.bluetooth_hfp_suspected
    assert any("A2DP" in c for c in report.checks)


def test_route_audit_virtual_sink_detected():
    pactl_sinks = "Sink #1\n\tName: pipetune-filter-chain\n\tDescription: PipeTune Virtual\n"
    report = diagnose.run_route_audit(
        pactl_info="",
        pactl_sinks=pactl_sinks,
        pactl_sources="",
        wpctl_status="",
    )
    assert report.has_virtual_sinks
    assert any("filter-chain" in c or "virtual" in c.lower() for c in report.checks)


def test_route_audit_is_readonly():
    report = diagnose.run_route_audit(
        pactl_info="",
        pactl_sinks="",
        pactl_sources="",
        wpctl_status="",
    )
    assert any("read-only" in c for c in report.checks)


# ---------------------------------------------------------------------------
# Route explain
# ---------------------------------------------------------------------------


def test_route_explain_content():
    lines = diagnose.build_route_explain_text()
    text = "\n".join(lines)
    assert "PipeWire" in text
    assert "WirePlumber" in text
    assert "default sink" in text.lower()
    assert "A2DP" in text
    assert "HSP" in text or "HFP" in text
    assert "read-only" in text.lower()


def test_route_explain_no_mutation_disclaimer():
    lines = diagnose.build_route_explain_text()
    text = "\n".join(lines)
    assert "No audio routing was changed." in text
    assert "No PipeWire, WirePlumber, ALSA" in text


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


def test_wireplumber_audit_json_schema():
    report = diagnose.run_wireplumber_audit(
        wpctl_status="",
        pactl_info="",
        pactl_sinks="",
        pactl_sources="",
        pactl_cards="",
        service_statuses=_make_service_statuses(),
    )
    output = render.render_wireplumber_audit_json(report)
    data = json.loads(output)
    assert "command" in data
    assert "pipetune_version" in data
    assert "collected_at" in data
    assert "host" in data
    assert "verdict" in data
    assert "checks" in data
    assert "warnings" in data
    assert "errors" in data
    assert "safety" in data
    assert data["safety"]["read_only"] is True
    assert data["safety"]["modified_system"] is False
    assert data["safety"]["restarted_services"] is False
    assert data["safety"]["changed_routing"] is False


def test_route_audit_json_schema():
    report = diagnose.run_route_audit(
        pactl_info="",
        pactl_sinks="",
        pactl_sources="",
        wpctl_status="",
    )
    output = render.render_route_audit_json(report)
    data = json.loads(output)
    assert "command" in data
    assert "pipetune_version" in data
    assert "collected_at" in data
    assert "host" in data
    assert "verdict" in data
    assert "safety" in data
    assert data["safety"]["read_only"] is True
    assert data["safety"]["changed_routing"] is False
    assert "bluetooth_hfp_suspected" in data
    assert "has_virtual_sinks" in data


def test_route_explain_json_schema():
    lines = diagnose.build_route_explain_text()
    output = render.render_route_explain_json(lines)
    data = json.loads(output)
    assert "command" in data
    assert "explanation" in data
    assert isinstance(data["explanation"], list)
    assert "safety" in data
    assert data["safety"]["read_only"] is True


def test_wireplumber_audit_json_version_matches():
    report = diagnose.run_wireplumber_audit(
        wpctl_status="",
        pactl_info="",
        pactl_sinks="",
        pactl_sources="",
        pactl_cards="",
        service_statuses=_make_service_statuses(),
    )
    data = json.loads(render.render_wireplumber_audit_json(report))
    assert data["pipetune_version"] == pipetune.__version__


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


def test_wireplumber_audit_cli_exits_zero(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        "pipetune.cli.run_wireplumber_audit",
        lambda **kw: WirePlumberAuditReport(
            passed=True,
            checks=["wireplumber: active", "wireplumber audit is read-only: no routing changed, no config modified"],
            warnings=[],
            errors=[],
            collected_at="2026-01-01T00:00:00+00:00",
        ),
    )
    exit_code = cli.main(["wireplumber", "audit"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "PipeTune WirePlumber Audit" in output
    assert "Final verdict: pass" in output
    assert "No audio routing was changed." in output


def test_wireplumber_audit_cli_json(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        "pipetune.cli.run_wireplumber_audit",
        lambda **kw: WirePlumberAuditReport(
            passed=True,
            checks=["ok"],
            warnings=[],
            errors=[],
            collected_at="2026-01-01T00:00:00+00:00",
        ),
    )
    exit_code = cli.main(["wireplumber", "audit", "--json"])
    output = capsys.readouterr().out
    assert exit_code == 0
    data = json.loads(output)
    assert data["verdict"] == "pass"
    assert data["safety"]["read_only"] is True


def test_wireplumber_audit_cli_exits_nonzero_on_fail(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        "pipetune.cli.run_wireplumber_audit",
        lambda **kw: WirePlumberAuditReport(
            passed=False,
            checks=[],
            warnings=[],
            errors=["no audio sinks detected"],
            collected_at="2026-01-01T00:00:00+00:00",
        ),
    )
    exit_code = cli.main(["wireplumber", "audit"])
    assert exit_code == 1


def test_route_audit_cli_exits_zero(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        "pipetune.cli.run_route_audit",
        lambda **kw: RouteAuditReport(
            passed=True,
            checks=["default output route: alsa_output", "route audit is read-only: no routing changed, no config modified"],
            warnings=[],
            errors=[],
            collected_at="2026-01-01T00:00:00+00:00",
        ),
    )
    exit_code = cli.main(["route", "audit"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "PipeTune Route Audit" in output
    assert "No audio routing was changed." in output


def test_route_audit_cli_json(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        "pipetune.cli.run_route_audit",
        lambda **kw: RouteAuditReport(
            passed=True,
            checks=["ok"],
            warnings=[],
            errors=[],
            bluetooth_hfp_suspected=False,
            collected_at="2026-01-01T00:00:00+00:00",
        ),
    )
    exit_code = cli.main(["route", "audit", "--json"])
    output = capsys.readouterr().out
    assert exit_code == 0
    data = json.loads(output)
    assert data["safety"]["read_only"] is True
    assert "bluetooth_hfp_suspected" in data


def test_route_explain_cli_exits_zero(capsys) -> None:
    exit_code = cli.main(["route", "explain"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "PipeWire" in output
    assert "WirePlumber" in output
    assert "read-only" in output.lower()


def test_route_explain_cli_json(capsys) -> None:
    exit_code = cli.main(["route", "explain", "--json"])
    output = capsys.readouterr().out
    assert exit_code == 0
    data = json.loads(output)
    assert data["command"] == "route explain"
    assert "explanation" in data
    assert data["safety"]["read_only"] is True


def test_wireplumber_audit_no_mutation(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        "pipetune.cli.run_wireplumber_audit",
        lambda **kw: WirePlumberAuditReport(
            passed=True, checks=["ok"], warnings=[], errors=[], collected_at="2026-01-01T00:00:00+00:00"
        ),
    )
    cli.main(["wireplumber", "audit"])
    output = capsys.readouterr().out
    assert "No audio routing was changed." in output
    assert "No PipeWire, WirePlumber, ALSA" in output


def test_route_audit_no_mutation(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        "pipetune.cli.run_route_audit",
        lambda **kw: RouteAuditReport(
            passed=True, checks=["ok"], warnings=[], errors=[], collected_at="2026-01-01T00:00:00+00:00"
        ),
    )
    cli.main(["route", "audit"])
    output = capsys.readouterr().out
    assert "No audio routing was changed." in output


# ---------------------------------------------------------------------------
# CI does not require live PipeWire/WirePlumber
# ---------------------------------------------------------------------------


def test_wireplumber_audit_works_without_live_services(monkeypatch) -> None:
    def fake_service_status(name: str):
        return (None, "command not found: systemctl")

    from pipetune.wireplumber import collect
    monkeypatch.setattr(collect, "collect_service_status", fake_service_status)
    monkeypatch.setattr(collect, "collect_wpctl_status", lambda: (False, "command not found: wpctl"))
    monkeypatch.setattr(collect, "collect_pactl_info", lambda: (False, "command not found: pactl"))
    monkeypatch.setattr(collect, "collect_pactl_sinks", lambda: (False, "command not found: pactl"))
    monkeypatch.setattr(collect, "collect_pactl_sources", lambda: (False, "command not found: pactl"))
    monkeypatch.setattr(collect, "collect_pactl_cards", lambda: (False, "command not found: pactl"))

    report = diagnose.run_wireplumber_audit()
    assert isinstance(report, WirePlumberAuditReport)
    assert report.verdict in ("pass", "warn", "fail")


def test_route_audit_works_without_live_services(monkeypatch) -> None:
    from pipetune.wireplumber import collect
    monkeypatch.setattr(collect, "collect_pactl_info", lambda: (False, "command not found: pactl"))
    monkeypatch.setattr(collect, "collect_pactl_sinks", lambda: (False, "command not found: pactl"))
    monkeypatch.setattr(collect, "collect_pactl_sources", lambda: (False, "command not found: pactl"))
    monkeypatch.setattr(collect, "collect_wpctl_status", lambda: (False, "command not found: wpctl"))

    report = diagnose.run_route_audit()
    assert isinstance(report, RouteAuditReport)


# ---------------------------------------------------------------------------
# Documentation
# ---------------------------------------------------------------------------


def test_docs_wireplumber_routing_diagnostics_exists() -> None:
    from pipetune.packaging import REPO_ROOT
    doc = REPO_ROOT / "docs" / "wireplumber-routing-diagnostics.md"
    assert doc.exists(), "docs/wireplumber-routing-diagnostics.md is missing"
