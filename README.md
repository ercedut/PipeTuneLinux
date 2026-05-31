# PipeTune Linux

PipeTune Linux is a safety-first Linux audio CLI for PipeWire-based systems.

## v0.2.1: HDA Hardware Quirk Audit
v0.2.1 keeps all v0.2.0 profile generation capabilities and adds a read-only hardware quirk audit layer for HDA pin-routing edge cases.

## What v0.2.1 Does
- Keeps all existing commands working: `version`, `doctor`, `devices`, `report`, `profile ...`.
- Parses and validates AutoEQ parametric EQ files.
- Generates PipeWire filter-chain config files without auto-installing them.
- Adds read-only hardware commands:
  - `pipetune hardware hda-audit`
  - `pipetune hardware mic-audit`
  - `pipetune hardware quirk-report`
- Generates local HDA/microphone quirk documentation bundles under `docs/system-audits/erce-hda-pin-retask/`.

## What v0.2.1 Does Not Do
- Does not modify system PipeWire/WirePlumber/ALSA configuration.
- Does not write automatically to `~/.config/pipewire`.
- Does not restart PipeWire/WirePlumber/ALSA.
- Does not auto-apply HDA retask changes.
- Does not install packages or run interactive retask tools.

## Installation
```bash
python -m pip install -e .
```

## Usage
```bash
pipetune --help
pipetune version
pipetune doctor
pipetune devices
pipetune report
pipetune report --output ./reports
```

## Profile Commands
```bash
pipetune profile parse examples/autoeq/sennheiser-hd650.txt
pipetune profile validate examples/autoeq/sennheiser-hd650.txt
pipetune profile generate examples/autoeq/sennheiser-hd650.txt --name "Sennheiser HD 650"
pipetune profile generate examples/autoeq/sennheiser-hd650.txt --name "Sennheiser HD 650" --output ./generated
```

### AutoEQ Input Example
```text
Preamp: -6.8 dB
Filter 1: ON PK Fc 20 Hz Gain -1.3 dB Q 2.000
Filter 2: ON PK Fc 31 Hz Gain -7.0 dB Q 0.500
Filter 3: ON PK Fc 63 Hz Gain 2.1 dB Q 1.200
```
This sample is for parser/generator testing and documentation only; it is not an official manufacturer profile.

### Generated Output Example
- `generated/sennheiser-hd-650.filter-chain.conf`

## Hardware Quirk Audit Commands
```bash
pipetune hardware hda-audit
pipetune hardware mic-audit
pipetune hardware quirk-report
```

Use these commands when the machine has historical HDA pin-routing quirks (speaker/headphone switching anomalies, manual retask history, unreliable built-in microphone). The audit is read-only and designed to preserve current working output paths.
Raw hardware audit captures are written under `docs/system-audits/.../raw/` locally and are gitignored by default.
Public Markdown files (`README.md`, `FIX_PLAN.md`, `PUBLIC_SUMMARY.md`) are sanitized summaries intended for sharing.

## Safety Statement
PipeTune Linux v0.2.1 is non-destructive by default.
It generates files and diagnostic reports but does not auto-install or auto-apply system audio changes.
PipeTune does not send audit data anywhere and does not perform external network reporting.

## Roadmap
- Current: v0.2.1 HDA Hardware Quirk Audit.
- Next: v0.3 safe speaker/headphone profile generation with hardware-quirk-aware guardrails.

See [docs/roadmap.md](docs/roadmap.md).

## Contribution Guide
1. Fork and create a feature branch.
2. Keep features scoped and test-covered.
3. Run `pytest` and CLI checks before opening a PR.
4. Document behavioral changes in `CHANGELOG.md`.

## License
MIT. See [LICENSE](LICENSE).
