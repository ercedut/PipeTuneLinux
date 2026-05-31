# Changelog

## [0.2.2] - 2026-05-31
### Added
- New `pipetune repair` command group with:
  - `pipetune repair hda-plan`
  - `pipetune repair backup-plan`
  - `pipetune repair mic-test-plan`
  - `pipetune repair checklist`
- Guided manual repair planning modules under `pipetune/repair/`.
- New documentation:
  - `docs/hda-repair-guide.md`
  - `docs/microphone-repair-guide.md`
- Test coverage for repair plan output and repair CLI behavior.

### Changed
- Project version updated to `0.2.2`.
- `pipetune version` codename updated to `Guided HDA Repair Planning`.
- README and roadmap updated for guided repair planning scope.

## [0.2.1] - 2026-05-31
### Added
- New `pipetune hardware` command group with:
  - `pipetune hardware hda-audit`
  - `pipetune hardware mic-audit`
  - `pipetune hardware quirk-report`
- Read-only HDA quirk audit collector for codec files, pin-config visibility, and retask reference signals.
- Read-only microphone route audit collector for ALSA/PipeWire source visibility and reliability warnings.
- Local quirk-report bundle generation under `docs/system-audits/erce-hda-pin-retask/` with:
  - command snapshots
  - HDA pin/config captures
  - `README.md`
  - `FIX_PLAN.md`
- New hardware quirk documentation in `docs/hardware-quirks.md`.
- Test coverage for HDA audit logic, mic audit logic, and hardware CLI integration.
- Sanitizer utilities for public hardware audit Markdown outputs.

### Changed
- Project version updated to `0.2.1`.
- `pipetune version` codename updated to `HDA Hardware Quirk Audit`.
- README and roadmap updated to include hardware quirk workflow and safety positioning.
- HDA retask-reference search now uses Python standard library scanning (no `rg` dependency).
- Quirk report output now separates public sanitized files from local-only raw captures under `raw/`.

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
