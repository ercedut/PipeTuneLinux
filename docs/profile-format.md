# Profile Format (v0.2.0)

## AudioProfile Model
`AudioProfile` fields:
- `name: str`
- `preamp_db: float | None`
- `filters: list[EqFilter]`
- `source_format: str`
- `warnings: list[str]`

This model represents a parsed profile before and after validation.

## EqFilter Model
`EqFilter` fields:
- `index: int`
- `enabled: bool`
- `filter_type: str`
- `frequency_hz: float`
- `gain_db: float`
- `q: float`

In v0.2.0 generation, enabled filters are mapped to PipeWire builtin biquad labels.

## ProfileValidationResult Model
`ProfileValidationResult` fields:
- `valid: bool`
- `errors: list[str]`
- `warnings: list[str]`

Generation rule:
- `errors` block config generation.
- `warnings` are allowed but must be surfaced to users.

## JSON-Ready Future Structure
v0.2.0 uses Python dataclasses, but the model is already suitable for future JSON serialization.
A future export format can represent:
- source metadata
- normalized filter list
- validator outputs
- generated target metadata (PipeWire/EasyEffects)

This is groundwork for v0.3 profile interoperability.
