# PipeTune Linux Roadmap

## v0.1 - Diagnostic Foundation (Done)
- Read-only CLI diagnostics for PipeWire, WirePlumber, ALSA, Bluetooth, and EasyEffects.
- Risk findings and report export (Markdown + JSON).

## v0.2 - Profile Generation Foundation (Current)
- Parse AutoEQ-style parametric EQ text files.
- Validate profile safety and compatibility.
- Generate candidate PipeWire filter-chain configuration files.
- File generation only: no auto-install, no restart, no system config mutation.

## v0.3 - Safe Device Profile Expansion (Next)
- Safe speaker/headphone profile generation workflow.
- Optional EasyEffects exporter for generated profile data.
- Additional compatibility guardrails and export validation.

## v0.4 - Benchmark and Measurement Tooling
- Repeatable command-line benchmarking and optional measurement collection helpers.
- Comparative profile validation workflow.

## v0.5 - WirePlumber Helper
- Session policy helper tooling for profile routing and policy diagnostics.
- Guardrails for non-destructive integration.

## v1.0 - Stable Profile Generation
- Stable and validated profile generation pipeline for supported devices/stacks.
- Documented compatibility matrix and migration path from diagnostics to profile use.

## v2.0 - GUI and Advanced Calibration
- Optional GUI workflow.
- Advanced calibration and guided tuning with strict safety defaults.
