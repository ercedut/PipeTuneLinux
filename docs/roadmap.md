# PipeTune Linux Roadmap

## v0.1 - Diagnostic Foundation (Done)
- Read-only CLI diagnostics for PipeWire, WirePlumber, ALSA, Bluetooth, and EasyEffects.
- Risk findings and report export (Markdown + JSON).

## v0.2 - Profile Generation Foundation (Done)
- Parse AutoEQ-style parametric EQ text files.
- Validate profile safety and compatibility.
- Generate candidate PipeWire filter-chain configuration files.
- File generation only: no auto-install, no restart, no system config mutation.

## v0.2.1 - HDA Hardware Quirk Audit (Done)
- Add read-only HDA pin retask and microphone route audits.
- Generate local hardware quirk report bundles for manual repair planning.
- Keep raw audit captures local-only and gitignored by default.
- Publish only sanitized hardware audit Markdown summaries.

## v0.2.2 - Guided HDA Repair Planning (Done)
- Add manual-only repair planning commands for HDA issues.
- Add backup-first and rollback-first planning outputs.
- Add explicit microphone verification planning with user-approved recording language.
- Keep all repair outputs non-destructive and read-only.

## v0.2.3 - Explicit Microphone Verification (Done)
- Add explicit user-approved microphone recording verification commands.
- Analyze local WAV captures and classify signal/silence/clipping safely.
- Keep recordings local-only and gitignored.
- Do not repair microphone routing automatically.

## v0.2.4 - Capture Gain State Audit (Done)
- Add read-only capture gain audit for Pulse/PipeWire source volume, mute state, wpctl volume, and ALSA card 0 mixer controls.
- Interpret clipping, silence, and usable signal as gain-staging evidence without claiming permanent repair.
- Print manual-only gain tuning plans and test matrices.
- Keep all commands non-destructive: no mixer changes, no service restarts, no ALSA state storage.

## v0.2.5 - Profile Safety Metadata and Activation Preflight (Done)
- Add generated profile manifests and safety metadata.
- Add profile safety-check and activation preflight commands.
- Add hardware quirk status for future profile activation.
- Decide whether future activation is ready, requires confirmation, blocked, or unknown.
- Keep all behavior preflight-only: no install, no activation, no PipeWire config writes.

## v0.3.0 - Safe Profile Activation (Done)
- Safe user-level profile installation workflow with explicit confirmation.
- Backup existing user-level config before overwrite.
- Record install manifests and checksums.
- Add rollback, list-installed, dry-run-install, and activation-status commands.
- Hardware-quirk-aware profile activation guardrails.
- No daemon, GUI, auto-switching, system-level install, or automatic service restart.

## v0.3.1 - Activation Hardening and State Integrity (Done)
- Refuse duplicate active profile installs.
- Detect stale manifests, orphan configs, checksum mismatches, duplicate active profiles, and rolled-back configs still present.
- Add state-doctor, verify-install, repair-state dry-run, and cleanup-rolled-back commands.
- Keep repair-state non-mutating until a future explicit confirmed repair flow exists.

## v0.4.0 - Measurement and Calibration Foundation (Current)
- Generate safe logarithmic sweep WAV files with metadata sidecars.
- Analyze recorded sweep WAV files for approximate response, level, clipping, and measurement quality.
- Import REW-style response CSVs into normalized PipeTune response data.
- Compare before/after response CSVs using shared-grid interpolation and simple variance metrics.
- Generate conservative correction draft TOML data only; no automatic profile application.
- Treat built-in laptop microphones as approximate and uncalibrated.

## v0.5 - WirePlumber Helper
- Session policy helper tooling for profile routing and policy diagnostics.
- Guardrails for non-destructive integration.

## v1.0 - Stable Profile Generation
- Stable and validated profile generation pipeline for supported devices/stacks.
- Documented compatibility matrix and migration path from diagnostics to profile use.

## v2.0 - GUI and Advanced Calibration
- Optional GUI workflow.
- Advanced calibration and guided tuning with strict safety defaults.
