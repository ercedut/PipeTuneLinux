# AutoEQ Import in PipeTune v0.2.0

## What AutoEQ Is
AutoEQ is a community-driven format and dataset ecosystem for headphone/speaker equalization presets.
PipeTune v0.2.0 supports importing common parametric EQ text lines from AutoEQ-style files.

## Supported Input Format
PipeTune supports:
- `Preamp: <value> dB`
- `Filter N: ON|OFF <type> Fc <freq> Hz Gain <gain> dB Q <q>`

Supported filter types:
- `PK`, `PEAK`, `PEAKING`
- `LS`, `LOW_SHELF`, `LOWSHELF`
- `HS`, `HIGH_SHELF`, `HIGHSHELF`

Parser behavior:
- Case-insensitive for keywords.
- Flexible whitespace.
- Ignores empty lines.
- Ignores comments starting with `#` or `//`.
- Ignores `OFF` filters for generation.

## Example
```text
Preamp: -6.8 dB
Filter 1: ON PK Fc 20 Hz Gain -1.3 dB Q 2.000
Filter 2: ON LS Fc 105 Hz Gain 1.5 dB Q 0.700
Filter 3: ON HS Fc 9000 Hz Gain -2.0 dB Q 1.200
```
The repository sample `examples/autoeq/sennheiser-hd650.txt` is a parser/generator test fixture, not an official HD650 tuning reference.

## Limitations in v0.2.0
- Text-based AutoEQ parsing only.
- No auto-installation to PipeWire directories.
- No automatic PipeWire restart.
- No real-time DSP control.

## Validation Rules
Errors:
- No filters found.
- Malformed filter line.
- Missing required filter values (frequency, gain, Q).
- Unsupported enabled filter type.
- Invalid numeric values.

Warnings:
- Missing preamp.
- Preamp above 0 dB.
- Boost above +6 dB.
- Frequency outside 10 Hz - 24000 Hz.
- Q outside 0.1 - 20.
- More than 20 filters.

Safety rule:
- `generate` refuses profiles with validation errors.
- `generate` allows warnings but prints them.
