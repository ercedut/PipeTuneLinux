# PipeTune Linux

PipeTune Linux is a safety-first Linux audio CLI for PipeWire-based systems.

## v0.3.0: Safe Profile Activation
v0.3.0 adds conservative user-level profile installation and rollback for generated PipeWire filter-chain configs.

## What v0.3.0 Does
- Keeps existing v0.1 through v0.2.5 commands working.
- Installs generated profiles only into `~/.config/pipewire/pipewire.conf.d/`.
- Requires `--user` and `--confirm-install` before writing user-level config.
- Requires `--confirm-hardware-quirk` when preflight returns `requires_confirmation`.
- Creates backups before overwriting existing user-level config files.
- Records install manifests with checksums.
- Provides rollback, list, activation-status, and dry-run commands.

## What v0.3.0 Does Not Do
- Does not use sudo.
- Does not write to `/etc`, `/lib`, `/sys`, `/proc`, or system audio configuration.
- Does not restart PipeWire, WirePlumber, ALSA, or the system automatically.
- Does not create daemons, GUI, services, or automatic profile switching.
- Does not install blocked or unknown preflight profiles.

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
pipetune profile rollback --latest --confirm-rollback
pipetune profile rollback <install_id> --confirm-rollback
```

## Privacy and Safety
- Recording requires explicit `--confirm-recording`.
- Generated repo-local configs and manifests are ignored by default.
- User-level install state is stored under `~/.local/share/pipetune/`.
- PipeTune does not upload recordings, manifests, or hardware audits.
- Mixer and hardware audit output can reveal device details; review output before sharing publicly.

## Roadmap
- Current: v0.3.0 Safe Profile Activation.
- Next: v0.4 benchmark and measurement tooling.

See [docs/roadmap.md](docs/roadmap.md).

## License
MIT. See [LICENSE](LICENSE).
