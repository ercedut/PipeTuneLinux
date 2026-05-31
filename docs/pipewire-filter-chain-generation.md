# PipeWire Filter-Chain Generation (v0.2.0)

## Purpose
PipeTune v0.2.0 generates PipeWire filter-chain configuration text from validated AutoEQ profiles.
The generated file is a starting point for manual review and manual deployment.

## Output Location
Default output directory:
- `generated/`

Default filename format:
- `<sanitized-profile-name>.filter-chain.conf`

Example:
- `generated/sennheiser-hd-650.filter-chain.conf`

## Why PipeTune Does Not Auto-Install Yet
v0.2.0 is intentionally generation-only for safety:
- Linux audio setups vary across distros and user environments.
- Automatic installation can disrupt active audio routing.
- Manual review keeps profile activation under user control.

PipeTune v0.2.0 therefore does **not**:
- write to `~/.config/pipewire`
- restart PipeWire
- patch WirePlumber policy files

## Future Direction
Future versions may add:
- dry-run install previews
- explicit opt-in integration workflows
- stronger compatibility checks before activation

## Safety Warnings
Generated configs are not guaranteed to be correct for every PipeWire version and system graph.
Always review and test manually before applying any generated config outside PipeTune.
