# PipeTune Linux

PipeTune Linux is a safety-first Linux audio CLI for PipeWire-based systems.

## v0.2.0: Profile Generation Foundation
v0.2.0 keeps the full v0.1 diagnostic toolchain and adds safe profile generation from AutoEQ text files.

Pipeline in v0.2.0:

AutoEQ Parametric EQ text
-> parse filters
-> validate safety and compatibility
-> create internal profile model
-> generate PipeWire filter-chain config text
-> write output file only

## What v0.2.0 Does
- Keeps all v0.1 commands working: `version`, `doctor`, `devices`, `report`.
- Parses common AutoEQ parametric EQ text format.
- Validates filter/preamp safety rules.
- Generates PipeWire filter-chain configuration files in a local output directory.
- Supports configurable output directory for generated files.

## What v0.2.0 Does Not Do
- Does not modify system PipeWire/WirePlumber/ALSA configuration.
- Does not write automatically to `~/.config/pipewire`.
- Does not restart PipeWire.
- Does not install or activate generated configs.
- Does not run as a daemon/service.

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

### New Profile Commands
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

## Safety Statement
PipeTune Linux v0.2.0 generates files only.
It does not auto-install or activate PipeWire configs.
No system configuration is modified by `pipetune profile generate`.

Why no auto-install yet:
- PipeWire/WirePlumber deployment patterns vary across distros and user setups.
- Safe generation-first reduces accidental breakage.
- v0.2.0 focuses on deterministic parsing/validation/generation behavior.

## Roadmap
- Current: v0.2.0 Profile Generation Foundation.
- Next: v0.3 safe speaker/headphone profile generation and optional EasyEffects exporter.

See [docs/roadmap.md](docs/roadmap.md).

## Contribution Guide
1. Fork and create a feature branch.
2. Keep features scoped and test-covered.
3. Run `pytest` and CLI checks before opening a PR.
4. Document behavioral changes in `CHANGELOG.md`.

## License
MIT. See [LICENSE](LICENSE).
