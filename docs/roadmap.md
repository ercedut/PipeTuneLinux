# PipeTune Linux Roadmap

## v0.1 - Diagnostic Foundation
- Read-only CLI diagnostics for PipeWire, WirePlumber, ALSA, Bluetooth, and EasyEffects.
- Risk findings and report export (Markdown + JSON).

## v0.2 - AutoEQ Parser and PipeWire Config Generator
- Parse AutoEQ-style datasets.
- Generate candidate PipeWire filter-chain configurations in a controlled workflow.

## v0.3 - Safe Speaker/Headphone Profile Generator
- Device-oriented profile templates.
- Safety checks around gain, channel mapping, and profile applicability.

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
