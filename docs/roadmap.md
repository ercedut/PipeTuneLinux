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

## v0.4.0 - Measurement and Calibration Foundation (Done)
- Generate safe logarithmic sweep WAV files with metadata sidecars.
- Analyze recorded sweep WAV files for approximate response, level, clipping, and measurement quality.
- Import REW-style response CSVs into normalized PipeTune response data.
- Compare before/after response CSVs using shared-grid interpolation and simple variance metrics.
- Generate conservative correction draft TOML data only; no automatic profile application.
- Treat built-in laptop microphones as approximate and uncalibrated.

## v0.4.1 - Measurement Accuracy and Safety Hardening (Done)
- Add read-only WAV inspection with clipping, silence, DC offset, sample format, channel count, and quality flags.
- Add normalized response validation with pass/warn/fail output.
- Harden REW import metadata and malformed-row handling.
- Harden response comparison band summaries and shared-grid overlap checks.
- Refuse correction drafts when response data quality fails.
- Document stable machine-readable measurement fields.

## v0.5.0 - LV2 Safeguard Plugin Foundation (Done)
- Add local-only LV2 safeguard plugin bundle.
- Implement conservative preamp/headroom, high-pass filtering, hard limiter, and bypass.
- Add local plugin build and offline validation commands.
- Keep plugin work non-mutating: no global install, no routing, no service restart.
- Avoid enhancer, bass booster, spatializer, or mastering-suite scope.

## v0.5.1 - LV2 Build, Metadata, and RT-Safety Hardening (Done)
- Harden local LV2 build dependency checks and Fedora error guidance.
- Add local build artifact cleanup and gitignore coverage for `.so`, `.o`, dependency, and temporary files.
- Add metadata validation for TTL files, plugin URI consistency, port documentation, and control ranges.
- Run optional `lv2_validate` when available without making it mandatory.
- Add RT-safety static checks focused on the LV2 `run()` callback path.
- Attempt compiled `.so` offline validation when a local build artifact is present.
- Keep DSP scope unchanged and keep plugin work non-mutating.

## v0.6.0 - Packaging and Installability Foundation (Done)
- Harden Python packaging metadata and deliberate source distribution inclusion.
- Add package inspect, build-check, and smoke-test commands.
- Add install and release checklist documentation.
- Verify source/wheel readiness without publishing packages.
- Keep normal verification rootless and non-mutating.

## v0.6.1 - Release Quality Gates and CI Foundation (Done)
- Add `pipetune package artifact-check` for local and staged artifact hygiene detection.
- Add `pipetune release check` as a single-command release gate with pass/warn/fail verdict.
- Add GitHub Actions CI with five jobs: tests, packaging, CLI smoke, artifact hygiene, plugin validation.
- Add `scripts/fresh-checkout-smoke.sh` for fresh-checkout install verification.
- Harden `package build-check` to clean up dist/ after inspection.
- Do not add GUI, daemon behavior, routing, global LV2 install, COPR automation, Flatpak, or DSP features.

## v0.7.0 - Device Profile Database and Contribution Workflow Foundation (Done)
- Community-maintainable profile database for headphones, laptop speakers, microphones, and Bluetooth.
- Profile metadata schema with quality classes (A/B/C/D), safety statuses, source tracking, and license fields.
- Profile validation command: `pipetune profiles validate-db`.
- Profile listing, search, and inspection commands: `pipetune profiles list/show/search`.
- Contribution templates and profile review documentation.
- Integration with release check and CI pipeline.
- No auto-apply, no global LV2 install, no audio routing, no system config mutation.
- Guardrails for non-destructive integration.

## v0.7.1 - Release Gate Cleanup and Profile DB Packaging Hardening (Done)
- Add `pipetune package clean-local` and `--dry-run` to remove safe local development artifacts.
- Improve artifact-check to distinguish removable artifacts from forbidden staged artifacts.
- Harden profile DB packaging: build-check now verifies profile DB exists and is included in MANIFEST.in.
- Release check recommends `clean-local` when only removable local artifacts are causing warn.
- After `clean-local`, release check returns `pass`.

## v0.8.0 - WirePlumber and Routing Diagnostics Foundation (Done)
- Read-only diagnostics for WirePlumber, PipeWire routing state, nodes, and default devices.
- `pipetune wireplumber audit`, `pipetune route audit`, `pipetune route explain`.
- No rule generation, no config writes, no service restarts.

## v0.8.1 - WirePlumber Rule Preview and Bluetooth Policy Hardening (Done)
- Preview-only WirePlumber rule generation (not installed).
- `pipetune bluetooth policy-audit` for Bluetooth profile diagnostics.
- `pipetune wireplumber suggest-rule --dry-run --user-only` writes only to repo-local preview paths.
- `pipetune wireplumber validate-preview` validates preview safety.
- `pipetune route recommend` provides routing improvement suggestions (read-only).

## v0.8.2 - CI LV2 Validator Dependency Handling Patch (Done)
- Fix: `lv2_validate` broken-helper failure (e.g., `sord_validate: not found`) is now a `warn` instead of `fail`.
- Real TTL validation errors still `fail`.
- CI installs `sord` to provide `sord_validate` alongside `lilv-utils`.
- CI diagnostic step shows validator tool availability before validation.

## v0.9.0 - User-Level WirePlumber Rule Install/Rollback Foundation (Done)
- Safe, explicit user-level WirePlumber rule installation from validated previews.
- `pipetune wireplumber install-rule --user-only --dry-run|--confirm-install`
- `pipetune wireplumber rollback-rule --dry-run|--confirm-rollback`
- `pipetune wireplumber rule-status` and `list-rules`
- Manifest-based install tracking, rollback support.
- No service restart. No routing change. No system config mutation.

## v0.9.1 - WirePlumber Rule Install State Integrity and Recovery (Done)
- State doctor, verify-rule, dry-run repair, cleanup rolled-back.
- Duplicate install protection (same checksum already active → refuse).
- Checksum mismatch detection (rollback refuses mismatched file deletion).
- Orphan file reporting.

## v0.9.2 - CI Green and WirePlumber Install Safety Polish (Done)
- Fix CI: remove non-existent Ubuntu package `sord`; `sord-validate` is optional (`|| true`).
- `pipetune wireplumber install-preflight`: read-only preflight before install-rule.
- `pipetune wireplumber install-guide`: safe step-by-step workflow for users.
- Release check gates: CI dependency check and WirePlumber install safety check.
- Preview artifact hygiene: `previews/wireplumber/*.lua` gitignored.
- Improved dry-run and confirmed install/rollback safety output.
- New docs: `wireplumber-rule-install-rollback.md`, `wireplumber-rule-state-integrity.md`.

## v1.0.0-rc1 - Stable Release Candidate and Safety Freeze (Current)
- RC audit, command matrix, mutation audit, docs check, and Fedora KDE smoke commands.
- Release check now includes RC mutation audit and docs check as gates.
- CI updated with RC audit job (`rc-gates`).
- Version 1.0.0rc1 (PEP 440); display v1.0.0-rc1.
- Safety boundaries and CLI interface frozen for stable release.
- New docs: `release-candidate.md`.

## v1.0.0 - Stable (Next)
- v1.0.0 Stable following successful RC1 validation, Fedora KDE manual smoke testing, and CI green.
- Safety freeze maintained from v1.0.0-rc1.

## v2.0 - GUI and Advanced Calibration
- Optional GUI workflow.
- Advanced calibration and guided tuning with strict safety defaults.
