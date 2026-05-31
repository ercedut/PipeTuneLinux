# Changelog

## [0.2.0] - 2026-05-31
### Added
- New `pipetune profile` command group with `parse`, `validate`, and `generate` subcommands.
- AutoEQ parametric EQ parser with tolerant whitespace/case handling and comment skipping.
- Profile data models (`AudioProfile`, `EqFilter`, `ProfileValidationResult`) for safe generation flow.
- Validation engine for filter presence, type support, numeric safety bounds, and warning/error separation.
- PipeWire filter-chain config generator with safe file output only (no install/restart/apply).
- Example AutoEQ input file and dedicated v0.2.0 profile documentation.
- New parser/validator/generator test coverage.

### Changed
- Project version updated to `0.2.0`.
- `pipetune version` now reports codename `Profile Generation Foundation`.
- `.gitignore` updated to ignore generated filter-chain `.conf` outputs by default.

## [0.1.0] - 2026-05-30
### Added
- Initial `pipetune` CLI with `version`, `doctor`, `devices`, and `report` commands.
- Safe command execution layer with timeout handling and missing-command resilience.
- PipeWire, WirePlumber, ALSA, Bluetooth, and EasyEffects diagnostic collectors.
- Risk engine with severity classification and conservative recommendation logic.
- Markdown and JSON diagnostic report generation.
- Baseline pytest suite for command execution, risk rules, and report structure.
- Core project documentation and architecture roadmap.
