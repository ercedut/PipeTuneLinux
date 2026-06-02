# PipeTune Linux

PipeTune Linux is a safety-first Linux audio CLI for PipeWire-based systems.

## v0.2.3: Explicit Microphone Verification
v0.2.3 adds explicit, user-approved microphone capture verification on top of the existing diagnostic, hardware audit, and repair-planning workflow.

## What v0.2.3 Does
- Keeps existing commands working: `version`, `doctor`, `devices`, `report`, `profile ...`, `hardware ...`, `repair ...`.
- Adds `verify` commands for microphone verification:
  - `pipetune verify mic-plan`
  - `pipetune verify mic-capture --duration 5 --confirm-recording`
  - `pipetune verify mic-analyze <wav_file>`
  - `pipetune verify mic-status`
- Distinguishes route visibility from actual capture signal verification.

## What v0.2.3 Does Not Do
- Does not repair microphone routing automatically.
- Does not modify ALSA/PipeWire/WirePlumber configuration.
- Does not restart audio services.
- Does not record unless explicit confirmation is passed.

## Installation
```bash
python -m pip install -e .
```

## Core Usage
```bash
pipetune version
pipetune doctor
pipetune hardware mic-audit
pipetune verify mic-plan
pipetune verify mic-status
```

## Explicit Mic Capture Flow
```bash
pipetune verify mic-capture --duration 5 --confirm-recording --analyze
pipetune verify mic-analyze verification/microphone/mic-test-YYYYMMDD-HHMMSS.wav
```

## Privacy and Safety
- Recording requires explicit `--confirm-recording`.
- Generated WAV/JSON verification artifacts are local-only and gitignored.
- PipeTune does not upload recordings.
- Review recordings before sharing; prefer analysis summaries over raw WAV files.
- No command in this release modifies system configuration automatically.

## Roadmap
- Current: v0.2.3 Explicit Microphone Verification.
- Next: v0.3 safe speaker/headphone profile generation with hardware-quirk-aware guardrails.

See [docs/roadmap.md](docs/roadmap.md).

## License
MIT. See [LICENSE](LICENSE).
