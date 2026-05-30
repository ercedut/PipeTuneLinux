# PipeTune Linux

PipeTune Linux is a read-only Linux audio diagnostic CLI focused on modern PipeWire-based systems.

## Problem Statement
Linux audio issues are often caused by stack mismatches, missing session services, profile mode conflicts, or device routing problems. Users need a safe baseline diagnostic before attempting enhancement or tuning.

## What v0.1.0 Does
- Inspects PipeWire, pipewire-pulse, and WirePlumber service status.
- Collects `pactl`, `wpctl`, `pw-dump`, and ALSA visibility.
- Detects default sink/source when visible.
- Detects Bluetooth audio card presence and profile hints.
- Detects EasyEffects availability.
- Evaluates conservative risk findings.
- Generates terminal summary and exportable Markdown/JSON reports.

## What v0.1.0 Does Not Do
- Does not modify system audio configuration.
- Does not apply DSP or EQ.
- Does not generate PipeWire filter-chain configurations.
- Does not write WirePlumber/ALSA/PipeWire config files.
- Does not require or invoke `sudo`.
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

## Example Report Paths
- `reports/audio-diagnostic-report.md`
- `reports/audio-diagnostic-report.json`

## Safety Statement
PipeTune Linux v0.1.0 is read-only.
It does not modify system audio configuration.
It does not apply DSP yet.
It is the diagnostic foundation for future Linux audio enhancement work.

## Roadmap
See [docs/roadmap.md](docs/roadmap.md).

## Contribution Guide
1. Fork and create a feature branch.
2. Keep features scoped and test-covered.
3. Run `pytest` and CLI checks before opening a PR.
4. Document behavioral changes in `CHANGELOG.md`.

## License
MIT. See [LICENSE](LICENSE).
