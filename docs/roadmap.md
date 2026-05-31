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

## v0.2.2 - Guided HDA Repair Planning (Current)
- Add manual-only repair planning commands for HDA issues.
- Add backup-first and rollback-first planning outputs.
- Add explicit microphone verification planning with user-approved recording language.
- Keep all repair outputs non-destructive and read-only.

## v0.3 - Safe Device Profile Expansion
- Safe speaker/headphone profile generation workflow.
- Optional EasyEffects exporter for generated profile data.
- Hardware-quirk-aware profile activation guardrails.

## v0.4 - Benchmark and Measurement Tooling
- Repeatable command-line benchmarking and optional measurement collection helpers.
- Comparative profile validation workflow.
- Ensure calibration/measurement workflows refuse unreliable built-in mics on quirk machines.

## v0.5 - WirePlumber Helper
- Session policy helper tooling for profile routing and policy diagnostics.
- Guardrails for non-destructive integration.

## v1.0 - Stable Profile Generation
- Stable and validated profile generation pipeline for supported devices/stacks.
- Documented compatibility matrix and migration path from diagnostics to profile use.

## v2.0 - GUI and Advanced Calibration
- Optional GUI workflow.
- Advanced calibration and guided tuning with strict safety defaults.
