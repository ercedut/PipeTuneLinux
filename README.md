# PipeTune Linux

PipeTune Linux is a safety-first Linux audio CLI for PipeWire-based systems.

## v0.4.0: Measurement and Calibration Foundation
v0.4.0 adds a read-only measurement command group for generating test sweeps, analyzing recorded sweep data, importing REW-style response CSVs, comparing responses, and creating conservative correction draft TOML files.

## What v0.4.0 Does
- Keeps existing v0.1 through v0.3.1 commands working.
- Installs generated profiles only into `~/.config/pipewire/pipewire.conf.d/`.
- Requires `--user` and `--confirm-install` before writing user-level config.
- Requires `--confirm-hardware-quirk` when preflight returns `requires_confirmation`.
- Creates backups before overwriting existing user-level config files.
- Records install manifests with checksums.
- Provides rollback, list, activation-status, and dry-run commands.
- Adds `state-doctor`, `verify-install`, dry-run repair proposals, and safe rolled-back manifest cleanup.
- Adds `pipetune measure` commands for local measurement files and draft correction data.

## What v0.4.0 Does Not Do
- Does not use sudo.
- Does not write to `/etc`, `/lib`, `/sys`, `/proc`, or system audio configuration.
- Does not restart PipeWire, WirePlumber, ALSA, or the system automatically.
- Does not create daemons, GUI, services, or automatic profile switching.
- Does not install blocked or unknown preflight profiles.
- Does not auto-apply generated measurement corrections.
- Does not claim sound quality improvement without measurement output.

## Installation
```bash
python -m pip install -e .
```

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

pipetune measure import-rew \
  --input measurements/rew/export.csv \
  --output measurements/imported/rew-normalized.csv

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

Measurement corrections are drafts only. PipeTune does not install them, apply them, restart services, or modify audio configuration.

## Privacy and Safety
- Recording requires explicit `--confirm-recording`.
- Generated repo-local configs and manifests are ignored by default.
- User-level install state is stored under `~/.local/share/pipetune/`.
- PipeTune does not upload recordings, manifests, or hardware audits.
- Mixer and hardware audit output can reveal device details; review output before sharing publicly.

## Roadmap
- Current: v0.4.0 Measurement and Calibration Foundation.
- Next: v0.5 WirePlumber helper.

See [docs/roadmap.md](docs/roadmap.md).

## License
MIT. See [LICENSE](LICENSE).
