# PipeTune Linux

PipeTune Linux is a safety-first Linux audio CLI for PipeWire-based systems.

## v0.2.4: Capture Gain State Audit
v0.2.4 adds a read-only capture gain audit and manual recommendation layer for unstable microphone gain staging.

## What v0.2.4 Does
- Keeps existing v0.1, v0.2, v0.2.1, v0.2.2, and v0.2.3 commands working.
- Adds `pipetune hardware gain-audit` for read-only Pulse/PipeWire and ALSA capture gain inspection.
- Adds `pipetune repair gain-plan` for a safe manual tuning sequence.
- Adds `pipetune repair gain-matrix` for structured manual baseline tests.
- Improves microphone analysis/status interpretation for clipping, silence, and usable signal cases.

## What v0.2.4 Does Not Do
- Does not change mixer values automatically.
- Does not modify ALSA, PipeWire, WirePlumber, HDA, or system configuration.
- Does not restart audio services.
- Does not record unless explicit `--confirm-recording` is passed.
- Does not run `sudo alsactl store`; persistence should wait until stable values are confirmed.

## Installation
```bash
python -m pip install -e .
```

## Core Usage
```bash
pipetune version
pipetune doctor
pipetune hardware mic-audit
pipetune hardware gain-audit
pipetune verify mic-status
pipetune repair gain-plan
pipetune repair gain-matrix
```

## Explicit Mic Capture Flow
```bash
pipetune verify mic-capture --duration 5 --confirm-recording --analyze
pipetune verify mic-analyze verification/microphone/mic-test-YYYYMMDD-HHMMSS.wav
```

## Manual Gain Tuning
PipeTune only prints manual commands and safety logic. Review the current audit first:
```bash
pipetune hardware gain-audit
pipetune repair gain-plan
pipetune repair gain-matrix
```

Manual command examples in PipeTune output are labeled `MANUAL / DO NOT RUN BLINDLY`. They are not executed by PipeTune.

## Privacy and Safety
- Recording requires explicit `--confirm-recording`.
- Generated WAV/JSON verification artifacts are local-only and gitignored.
- PipeTune does not upload recordings.
- Mixer audit output can reveal device details; review raw command output before sharing publicly.
- No command in this release modifies system configuration automatically.

## Roadmap
- Current: v0.2.4 Capture Gain State Audit.
- Next: v0.3 safe speaker/headphone profile generation with hardware-quirk-aware guardrails.

See [docs/roadmap.md](docs/roadmap.md).

## License
MIT. See [LICENSE](LICENSE).
