# Changelog

## [0.4.0] - 2026-06-02
### Added
- New `pipetune measure` command group.
- New `pipetune measure generate-sweep` command for safe logarithmic mono WAV sweep generation with sidecar metadata.
- New `pipetune measure analyze-sweep` command for approximate FFT-based response reports, level checks, clipping detection, and optional CSV output.
- New `pipetune measure import-rew` command for REW-style CSV import into normalized `freq_hz,magnitude_db` data.
- New `pipetune measure compare-response` command for before/after response comparison with shared-grid interpolation and variance wording.
- New `pipetune measure generate-correction` command for conservative draft TOML correction data.
- New `pipetune/measurement/` package and measurement documentation.

### Changed
- Project version updated to `0.4.0`.
- `pipetune version` codename updated to `Measurement and Calibration Foundation`.
- README and roadmap updated for the v0.4 measurement workflow.

### Safety
- Sweep amplitudes above `0.9` are refused.
- Correction generation requires `--safe`, limits boost to `+3 dB`, adds laptop-speaker high-pass metadata, includes preamp headroom, and never applies profiles automatically.
- Built-in laptop microphones are documented as approximate and uncalibrated.
- Measurement commands do not modify PipeWire, WirePlumber, ALSA, user audio configs, or system audio configs.

## [0.3.1] - 2026-06-02
### Added
- Duplicate active install protection for profile install.
- New `pipetune profile state-doctor` command for activation state integrity reports.
- New `pipetune profile verify-install <install_id>` command.
- New `pipetune profile repair-state --dry-run` command.
- New `pipetune profile cleanup-rolled-back --confirm-cleanup` command.
- State integrity checks for missing configs, orphan configs, checksum mismatches, duplicate active profiles, corrupted manifests, and rolled-back configs still present.

### Changed
- Project version updated to `0.3.1`.
- `pipetune version` codename updated to `Activation Hardening and State Integrity`.
- `pipetune profile list-installed` now reports profile ID, config existence, checksum state, status, and install time.
- `pipetune profile activation-status` now reports integrity counts and explicit warnings.
- Rollback errors are clearer for unknown IDs and already rolled-back IDs.

### Safety
- Duplicate installs are refused instead of creating redundant manifests.
- Rollback continues to refuse checksum mismatches.
- `repair-state` is dry-run only and modifies nothing.
- `cleanup-rolled-back` removes only rolled-back manifest entries whose config files are absent.

## [0.3.0] - 2026-06-02
### Added
- New `pipetune profile dry-run-install <generated_config_file> --user` command.
- New `pipetune profile install <generated_config_file> --user --confirm-install` command.
- New `pipetune profile list-installed` command.
- New `pipetune profile activation-status` command.
- New `pipetune profile rollback <install_id> --confirm-rollback` and `pipetune profile rollback --latest --confirm-rollback` commands.
- New `pipetune/activation/` package for user-level install paths, backups, install manifests, status, and rollback.
- New documentation:
  - `docs/safe-profile-activation.md`
  - `docs/profile-rollback.md`

### Changed
- Project version updated to `0.3.0`.
- `pipetune version` codename updated to `Safe Profile Activation`.
- README and roadmap updated for conservative user-level activation.
- `.gitignore` updated for local activation test/runtime state.

### Safety
- Installs are user-level only under `~/.config/pipewire/pipewire.conf.d/`.
- Install requires `--user --confirm-install`.
- Hardware-quirk-sensitive installs require `--confirm-hardware-quirk`.
- PipeTune creates backups and install manifests before writing user-level config.
- PipeTune does not restart services automatically.
- Rollback verifies checksums before removing installed files.

## [0.2.5] - 2026-06-02
### Added
- New `pipetune profile manifest <generated_config_file> --name <name> --type <type>` command.
- New `pipetune profile safety-check <generated_config_file>` command.
- New `pipetune profile preflight <generated_config_file>` command.
- New `pipetune hardware quirk-status` command.
- New `pipetune/safety/` package for safety metadata, manifests, preflight checks, quirk metadata, and readiness decisions.
- New documentation:
  - `docs/profile-safety-metadata.md`
  - `docs/activation-preflight.md`

### Changed
- Project version updated to `0.2.5`.
- `pipetune version` codename updated to `Profile Safety Metadata and Activation Preflight`.
- Generated PipeWire configs now include additional safety metadata comments.
- `.gitignore` now ignores generated manifest, preflight, and safety JSON artifacts.
- README and roadmap updated for the preflight-only v0.2.5 scope.

### Safety
- v0.2.5 does not install, activate, or apply profiles.
- v0.2.5 does not write to system or user PipeWire configuration.
- Activation preflight reports readiness only: `ready`, `requires_confirmation`, `blocked`, or `unknown`.

## [0.2.4] - 2026-06-02
### Added
- New `pipetune hardware gain-audit` command for read-only capture gain state inspection.
- New `pipetune repair gain-plan` command for manual-only gain tuning guidance.
- New `pipetune repair gain-matrix` command for structured manual capture baseline testing.
- New modular gain package under `pipetune/gain/` with parsers, models, audit collection, and recommendations.
- New documentation:
  - `docs/capture-gain-audit.md`

### Changed
- Project version updated to `0.2.4`.
- `pipetune version` codename updated to `Capture Gain State Audit`.
- `pipetune verify mic-analyze` now prints richer clipping, silence, and signal interpretation.
- `pipetune verify mic-status` now includes a suggested next action from the latest safe status summary.
- README, roadmap, microphone verification, and microphone repair docs updated for capture gain audit workflow.

### Safety
- Gain audit and repair outputs are read-only.
- PipeTune does not change ALSA/PipeWire/WirePlumber/HDA settings.
- PipeTune prints manual commands only and warns against storing ALSA state before stable values are confirmed.

## [0.2.3] - 2026-05-31
### Added
- New `pipetune verify` command group with:
  - `pipetune verify mic-plan`
  - `pipetune verify mic-capture --duration <seconds> --confirm-recording`
  - `pipetune verify mic-analyze <wav_file>`
  - `pipetune verify mic-status`
- Explicit WAV signal analysis (duration/sample-rate/channels/peak/rms/silence/clipping/status).
- Verification output directory scaffolding:
  - `verification/.gitkeep`
  - `verification/microphone/.gitkeep`
- New docs:
  - `docs/microphone-verification.md`

### Changed
- Project version updated to `0.2.3`.
- `pipetune version` codename updated to `Explicit Microphone Verification`.
- `.gitignore` updated to ignore local microphone verification WAV/JSON/TXT artifacts.
- Microphone repair docs updated with explicit verify workflow and privacy sharing guidance.

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
