# PipeTune Linux

PipeTune Linux is a safety-first Linux audio CLI for PipeWire-based systems.

## v0.2.5: Profile Safety Metadata and Activation Preflight
v0.2.5 adds generated profile manifests, safety checks, hardware quirk status, and activation preflight decisions before any future install flow exists.

## What v0.2.5 Does
- Keeps existing v0.1 through v0.2.4 commands working.
- Adds `pipetune profile manifest` for generated profile safety metadata.
- Adds `pipetune profile safety-check` for local generated config inspection.
- Adds `pipetune profile preflight` for future activation readiness decisions.
- Adds `pipetune hardware quirk-status` for machine-level activation risk.
- Keeps capture gain audit and explicit microphone verification workflows intact.

## What v0.2.5 Does Not Do
- Does not install profiles.
- Does not activate profiles.
- Does not modify PipeWire, WirePlumber, ALSA, HDA, or system audio configuration.
- Does not write to `~/.config/pipewire`, `/etc`, `/lib`, `/sys`, or `/proc`.
- Does not restart audio services.
- Does not create daemons, GUI, rollback, or automatic switching.

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

## Profile Safety Flow
```bash
pipetune profile generate examples/autoeq/sennheiser-hd650.txt --name "Sennheiser HD 650"
pipetune profile manifest generated/sennheiser-hd-650.filter-chain.conf --name "Sennheiser HD 650" --type headphone
pipetune profile safety-check generated/sennheiser-hd-650.filter-chain.conf
pipetune profile preflight generated/sennheiser-hd-650.filter-chain.conf
```

Generated configs and manifests remain local generated artifacts and are gitignored by default.

## Explicit Mic Capture Flow
```bash
pipetune verify mic-capture --duration 5 --confirm-recording --analyze
pipetune verify mic-analyze verification/microphone/mic-test-YYYYMMDD-HHMMSS.wav
```

## Privacy and Safety
- Recording requires explicit `--confirm-recording`.
- Generated WAV/JSON verification artifacts are local-only and gitignored.
- PipeTune does not upload recordings, manifests, or hardware audits.
- Mixer and hardware audit output can reveal device details; review output before sharing publicly.
- Every v0.2.5 preflight command reports that no system configuration was modified.

## Roadmap
- Current: v0.2.5 Profile Safety Metadata and Activation Preflight.
- Next: v0.3 safe user-level profile activation with explicit install confirmation.

See [docs/roadmap.md](docs/roadmap.md).

## License
MIT. See [LICENSE](LICENSE).
