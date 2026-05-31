# PipeTune Linux

PipeTune Linux is a safety-first Linux audio CLI for PipeWire-based systems.

## v0.2.2: Guided HDA Repair Planning
v0.2.2 keeps the v0.2.1 read-only hardware audit workflow and adds guided manual repair planning commands.

## What v0.2.2 Does
- Keeps all existing commands working: `version`, `doctor`, `devices`, `report`, `profile ...`, `hardware ...`.
- Parses/validates AutoEQ files and generates PipeWire filter-chain config files without auto-installing them.
- Audits HDA and microphone route state in read-only mode.
- Adds guided repair planning commands:
  - `pipetune repair hda-plan`
  - `pipetune repair backup-plan`
  - `pipetune repair mic-test-plan`
  - `pipetune repair checklist`

## What v0.2.2 Does Not Do
- Does not modify system PipeWire/WirePlumber/ALSA configuration.
- Does not write automatically to `~/.config/pipewire`.
- Does not restart PipeWire/WirePlumber/ALSA.
- Does not auto-apply HDA retask changes.
- Does not run `hdajackretask`.

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
```

## Hardware Quirk Audit Commands
```bash
pipetune hardware hda-audit
pipetune hardware mic-audit
pipetune hardware quirk-report
```

## Guided Repair Planning Commands
```bash
pipetune repair hda-plan
pipetune repair backup-plan
pipetune repair mic-test-plan
pipetune repair checklist
```

## Privacy and Safety
- Repair plans are local and manual-only.
- Raw hardware audit captures are local-only under `docs/system-audits/.../raw/` and gitignored by default.
- Public Markdown files are sanitized summaries.
- PipeTune does not upload audit data anywhere.
- Microphone capture tests are never automatic.
- Any recording file is created only by manual user action.

## Roadmap
- Current: v0.2.2 Guided HDA Repair Planning.
- Next: v0.3 safe speaker/headphone profile generation with hardware-quirk-aware guardrails.

See [docs/roadmap.md](docs/roadmap.md).

## License
MIT. See [LICENSE](LICENSE).
