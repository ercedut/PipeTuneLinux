# Architecture

## CLI Layer
`pipetune.cli` provides command routing:
- `version`
- `doctor`
- `devices`
- `report`

## Collectors Layer
`pipetune.collectors` gathers stack-specific state without mutation:
- `pipewire.py`
- `wireplumber.py`
- `alsa.py`
- `bluetooth.py`
- `easyeffects.py`
- shared runner in `command.py`

## Risk Engine
`pipetune.risk` evaluates collected data into ordered severities:
- critical
- high
- medium
- low
- info

It also generates conservative recommendations from findings.

## Report Generators
`pipetune.reports` produces:
- Markdown report for human review
- JSON report for future machine consumers

## Future Profile Generator
Planned for v0.2+:
- profile synthesis layer consuming stable JSON diagnostics
- rule-checked outputs before any user-applied changes

## Future PipeWire Filter-Chain Backend
Planned for v0.2+:
- backend for generating filter-chain snippets
- strict separation from read-only diagnostics
- explicit user acceptance before any write/apply action
