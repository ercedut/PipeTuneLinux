# PipeTune Linux

PipeTune Linux is a safety-first Linux audio CLI for PipeWire-based systems.

**Current version: v1.0.0-rc1 — Stable Release Candidate and Safety Freeze**

> **Release Candidate Notice:** v1.0.0-rc1 is the first stable release candidate. Safety boundaries and CLI interfaces are frozen. See [docs/release-candidate.md](docs/release-candidate.md) for what is frozen, known limitations, and how to run the Fedora KDE smoke test.

## What PipeTune Is

PipeTune Linux is a read-only-first CLI for:
- Audio system diagnostics (PipeWire, WirePlumber, ALSA, Bluetooth)
- Safe user-level WirePlumber rule management (install, rollback, state tracking)
- Acoustic measurement and response analysis (sweep generation, REW import, correction drafts)
- Device profile database (headphones, laptop speakers, microphones, Bluetooth)
- LV2 safeguard plugin tooling (local build and validation only)
- Release quality gates and packaging verification

## What PipeTune Is Not

PipeTune does **not**:
- Change default audio routing or sinks/sources
- Restart PipeWire, WirePlumber, or any service automatically
- Install the LV2 plugin globally
- Route audio through the LV2 plugin automatically
- Create a daemon, background service, or GUI
- Claim audio improvement without measurement evidence
- Use `sudo` or write to `/etc`, `/usr`, `/lib`, or `/sys`
- Publish packages or upload diagnostics to external services

## Quick Start

```bash
git clone <repo-url>
cd PipeTuneLinux
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
pipetune version
pipetune doctor
pipetune package inspect
```

See [docs/install.md](docs/install.md) for full installation instructions.

## Release Candidate Warning

v1.0.0-rc1 is a release candidate. It is suitable for evaluation, testing, and daily diagnostic use on Fedora KDE and compatible systems. Production deployment should wait for v1.0.0 Stable.

## Safe Command Examples

```bash
# System diagnostics (read-only)
pipetune version
pipetune doctor
pipetune hardware quirk-status
pipetune hardware gain-audit

# WirePlumber diagnostics (read-only)
pipetune wireplumber audit
pipetune route audit
pipetune bluetooth policy-audit

# WirePlumber rule workflow (safe, explicit)
pipetune wireplumber install-guide
pipetune wireplumber install-preflight
pipetune wireplumber suggest-rule --user-only --dry-run
pipetune wireplumber install-rule previews/wireplumber/my-rule.lua --user-only --dry-run
pipetune wireplumber install-rule previews/wireplumber/my-rule.lua --user-only --confirm-install
pipetune wireplumber rule-state-doctor
pipetune wireplumber rollback-rule <install_id> --confirm-rollback

# Release-candidate gates (read-only)
pipetune rc audit
pipetune rc mutation-audit
pipetune rc docs-check
pipetune rc command-matrix
pipetune rc fedora-smoke

# Release quality gate
pipetune release check
```

## Fedora KDE Smoke Test

Run the complete non-mutating smoke suite:

```bash
pipetune rc fedora-smoke
pipetune rc fedora-smoke --json
```

A `pass` or `warn` verdict is acceptable. `warn` is expected when Bluetooth hardware or live audio services are absent. `fail` blocks release.

## Installation

```bash
python -m pip install -e .
```

See [docs/install.md](docs/install.md) for fresh-checkout installation, optional LV2 build dependencies, cleanup, and uninstall steps.

## Core Usage

```bash
pipetune version
pipetune doctor
pipetune hardware quirk-status
pipetune hardware gain-audit
pipetune verify mic-status
```

## Profile Activation Flow

```bash
pipetune profile generate examples/autoeq/sennheiser-hd650.txt --name "Sennheiser HD 650"
pipetune profile manifest generated/sennheiser-hd-650.filter-chain.conf --name "Sennheiser HD 650" --type headphone
pipetune profile preflight generated/sennheiser-hd-650.filter-chain.conf
pipetune profile dry-run-install generated/sennheiser-hd-650.filter-chain.conf --user
pipetune profile install generated/sennheiser-hd-650.filter-chain.conf --user --confirm-install
```

On hardware-quirk-sensitive machines, install also requires:
```bash
pipetune profile install generated/sennheiser-hd-650.filter-chain.conf --user --confirm-install --confirm-hardware-quirk
```

PipeTune prints the manual restart command but does not run it:
```
systemctl --user restart pipewire pipewire-pulse wireplumber
```

## Installed Profile Commands

```bash
pipetune profile list-installed
pipetune profile activation-status
pipetune profile state-doctor
pipetune profile verify-install <install_id>
pipetune profile repair-state --dry-run
pipetune profile cleanup-rolled-back --confirm-cleanup
pipetune profile rollback --latest --confirm-rollback
pipetune profile rollback <install_id> --confirm-rollback
```

## Measurement Commands

```bash
pipetune measure generate-sweep \
  --output measurements/sweeps/log-sweep-48k.wav \
  --duration 10 \
  --sample-rate 48000

pipetune measure validate-response \
  --input measurements/imported/rew-normalized.csv

pipetune measure compare-response \
  --before measurements/before.csv \
  --after measurements/after.csv \
  --output measurements/reports/response-comparison.json
```

Measurement corrections are drafts only. PipeTune does not install them, apply them, restart services, or modify audio configuration. Response comparison reports `flatter_by_variance`; it does not claim better sound.

## LV2 Safeguard Plugin

```bash
pipetune plugin info
pipetune plugin build --local
pipetune plugin clean --local
pipetune plugin validate --metadata
pipetune plugin validate --rt-safety
```

The plugin is a conservative local safeguard: preamp/headroom, mandatory high-pass filtering, and a hard safety limiter. It is not installed globally and not routed into PipeWire automatically.

## Package Verification

```bash
pipetune package inspect
pipetune package build-check
pipetune package smoke-test
pipetune package artifact-check
pipetune package clean-local --dry-run
pipetune package clean-local
```

## Release Quality Gates

```bash
pipetune release check
pipetune release check --json
```

`release check` runs all local gates: version metadata, required files, package checks, plugin validation, profile DB, RC mutation audit, and RC docs check.

See [docs/release-checklist.md](docs/release-checklist.md) for the full release sequence.

## WirePlumber and Routing Diagnostics

```bash
pipetune wireplumber audit
pipetune route audit
pipetune route explain
pipetune route recommend
```

All commands are read-only. See [docs/wireplumber-routing-diagnostics.md](docs/wireplumber-routing-diagnostics.md).

## WirePlumber Rule Preview and Bluetooth Policy

```bash
pipetune bluetooth policy-audit
pipetune wireplumber suggest-rule --user-only --dry-run
pipetune wireplumber validate-preview previews/wireplumber/my-rule.lua
```

See [docs/bluetooth-policy-diagnostics.md](docs/bluetooth-policy-diagnostics.md) and [docs/wireplumber-rule-preview.md](docs/wireplumber-rule-preview.md).

## WirePlumber Rule Install/Rollback

```bash
pipetune wireplumber install-guide
pipetune wireplumber install-preflight
pipetune wireplumber install-rule previews/wireplumber/my-rule.lua --user-only --dry-run
pipetune wireplumber install-rule previews/wireplumber/my-rule.lua --user-only --confirm-install
pipetune wireplumber rule-state-doctor
pipetune wireplumber rollback-rule <install_id> --confirm-rollback
```

No service is restarted. Rule takes effect only after manual WirePlumber reload. See [docs/wireplumber-rule-install-rollback.md](docs/wireplumber-rule-install-rollback.md).

## Device Profile Database

```bash
pipetune profiles list
pipetune profiles show <profile_id>
pipetune profiles search laptop
pipetune profiles validate-db
```

Profile commands are read-only. See [docs/profile-database.md](docs/profile-database.md) and [docs/profile-contribution-guide.md](docs/profile-contribution-guide.md).

## Privacy and Safety

- Recording requires explicit `--confirm-recording`.
- Generated repo-local configs and manifests are gitignored by default.
- User-level install state is stored under `~/.local/share/pipetune/`.
- PipeTune does not upload recordings, manifests, or hardware audits.

## Roadmap

- Current: v1.0.0-rc1 Stable Release Candidate and Safety Freeze.
- Next: v1.0.0 Stable.

See [docs/roadmap.md](docs/roadmap.md).

## License

MIT. See [LICENSE](LICENSE).
