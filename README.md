# PipeTune Linux

PipeTune Linux is a safety-first Linux audio CLI for PipeWire-based systems.

## v0.6.0: Packaging and Installability Foundation
v0.6.0 makes PipeTune Linux cleaner to install, verify, and prepare for release from a fresh checkout. It adds package inspection, build readiness checks, smoke tests, install docs, and a release checklist without adding GUI, daemon, routing, install, or DSP behavior.

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

## What v0.6.0 Does
- Keeps existing v0.1 through v0.3.1 commands working.
- Installs generated profiles only into `~/.config/pipewire/pipewire.conf.d/`.
- Requires `--user` and `--confirm-install` before writing user-level config.
- Requires `--confirm-hardware-quirk` when preflight returns `requires_confirmation`.
- Creates backups before overwriting existing user-level config files.
- Records install manifests with checksums.
- Provides rollback, list, activation-status, and dry-run commands.
- Adds `state-doctor`, `verify-install`, dry-run repair proposals, and safe rolled-back manifest cleanup.
- Adds `pipetune measure` commands for local measurement files and draft correction data.
- Adds `inspect-wav` and `validate-response` for measurement trust checks.
- Adds a local LV2 safeguard plugin bundle under `plugins/lv2/pipetune-safeguard.lv2/`.
- Adds `pipetune plugin info`, `pipetune plugin build --local`, `pipetune plugin clean --local`, `pipetune plugin validate --offline`, `pipetune plugin validate --metadata`, and `pipetune plugin validate --rt-safety`.
- Keeps local plugin build artifacts out of expected commit artifacts.
- Adds `pipetune package inspect`, `pipetune package build-check`, and `pipetune package smoke-test`.
- Adds explicit install and release checklist documentation.

## What v0.6.0 Does Not Do
- Does not use sudo.
- Does not write to `/etc`, `/lib`, `/sys`, `/proc`, or system audio configuration.
- Does not restart PipeWire, WirePlumber, ALSA, or the system automatically.
- Does not create daemons, GUI, services, or automatic profile switching.
- Does not install blocked or unknown preflight profiles.
- Does not auto-apply generated measurement corrections.
- Does not claim sound quality improvement without measurement output.
- Does not improve sound directly; it improves measurement trustworthiness before any later plugin or daemon work.
- Does not install the LV2 plugin globally.
- Does not auto-route audio through the LV2 plugin.
- Does not build an audio enhancer, spatializer, mastering suite, or bass booster.
- Does not publish packages.
- Does not add Fedora COPR automation.
- Does not add Flatpak packaging.

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
```bash
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
  --sample-rate 48000 \
  --start-hz 20 \
  --end-hz 20000 \
  --amplitude 0.5

pipetune measure analyze-sweep \
  --sweep measurements/sweeps/log-sweep-48k.wav \
  --recorded measurements/recordings/laptop-speaker-recorded.wav \
  --output measurements/reports/laptop-speaker-response.json \
  --csv-output measurements/reports/laptop-speaker-response.csv

pipetune measure inspect-wav \
  --input measurements/recordings/laptop-speaker-recorded.wav

pipetune measure import-rew \
  --input measurements/rew/export.csv \
  --output measurements/imported/rew-normalized.csv

pipetune measure validate-response \
  --input measurements/imported/rew-normalized.csv

pipetune measure compare-response \
  --before measurements/before.csv \
  --after measurements/after.csv \
  --output measurements/reports/response-comparison.json

pipetune measure generate-correction \
  --input measurements/imported/rew-normalized.csv \
  --output profiles/speakers/laptop-correction-draft.toml \
  --target flat \
  --safe
```

Measurement corrections are drafts only. PipeTune does not install them, apply them, restart services, or modify audio configuration. Response comparison reports `flatter_by_variance`; it does not claim better sound.

## LV2 Safeguard Plugin
```bash
pipetune plugin info
pipetune plugin build --local
pipetune plugin clean --local
pipetune plugin validate --offline
pipetune plugin validate --metadata
pipetune plugin validate --metadata --json
pipetune plugin validate --rt-safety
```

The plugin is a conservative local safeguard foundation: preamp/headroom, mandatory high-pass filtering, and a hard safety limiter. It is not installed globally and is not routed into PipeWire automatically. Build artifacts stay under `plugins/lv2/pipetune-safeguard.lv2/` and are gitignored.

Fedora local build dependencies:
```bash
sudo dnf install gcc make lv2-devel
```

PipeTune checks for missing `gcc`, `make`, and LV2 headers before local builds, but it never runs dependency installation automatically. If `lv2_validate` is installed, metadata validation runs it; if it is missing, PipeTune reports a warning instead of adding a mandatory external validation dependency.

The limiter is a hard safety limiter only. It exists to cap samples at a configured ceiling; it is not a mastering limiter and should not be described as improving sound quality.

## Package Verification
```bash
pipetune package inspect
pipetune package build-check
pipetune package smoke-test
```

`package inspect` reports local package metadata and project layout. `package build-check` verifies packaging readiness without uploading anything; if the optional `build` module is missing, install it manually with:

```bash
python -m pip install build
```

`package smoke-test` runs non-mutating CLI checks, including version, doctor, state-doctor, measurement fixture validation, plugin info, and plugin metadata validation.

## Privacy and Safety
- Recording requires explicit `--confirm-recording`.
- Generated repo-local configs and manifests are ignored by default.
- User-level install state is stored under `~/.local/share/pipetune/`.
- PipeTune does not upload recordings, manifests, or hardware audits.
- Mixer and hardware audit output can reveal device details; review output before sharing publicly.

## Roadmap
- Current: v0.6.0 Packaging and Installability Foundation.
- Next: v0.6.x packaging hardening or v0.7 routing diagnostics.

See [docs/roadmap.md](docs/roadmap.md).

## License
MIT. See [LICENSE](LICENSE).
