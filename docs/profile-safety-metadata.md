# Profile Safety Metadata

## 1. Purpose
Profile safety metadata describes what a generated profile is, where it came from, what device type it targets, and whether future activation requires manual confirmation.

## 2. Why Safety Metadata Exists
Generated EQ files are not enough for safe activation. PipeTune must know profile type, generator version, source format, preamp/headroom, filter count, gain range, and hardware quirk sensitivity before v0.3 can install anything.

## 3. Profile Types
Allowed profile types are:
- `headphone`
- `laptop_speaker`
- `microphone`
- `bluetooth`
- `system`
- `unknown`

Unknown profile types are not suitable for activation.

## 4. Hardware Quirk Metadata
Hardware quirk metadata records whether this machine has routing risks such as manual HDA pin retask, unknown HDA routing, or microphone gain instability. If an HDA quirk is detected, automatic switching is not safe and manual output confirmation is required.

## 5. Activation Readiness Statuses
- `ready`: safe enough for a future v0.3 user-level installation flow.
- `requires_confirmation`: usable only after explicit physical output confirmation.
- `blocked`: must not be activated until issues are fixed.
- `unknown`: not enough metadata to decide.

## 6. Manifest Structure
`pipetune profile manifest` writes a JSON file next to a generated filter-chain config. It contains:
- config path
- generator name and version
- profile safety metadata
- preamp and gain summary
- filter count and labels
- manual confirmation requirements
- warnings

Generated manifests are local generated artifacts and ignored by default under `generated/*.manifest.json`.

## 7. What Preflight Checks
Preflight combines generated config safety checks, manifest metadata, hardware quirk status, profile type, auto-apply safety, and manual output confirmation requirements.

## 8. What Preflight Does Not Do
- Does not install profiles.
- Does not activate profiles.
- Does not write PipeWire configuration.
- Does not restart PipeWire or WirePlumber.
- Does not switch output devices automatically.

## 9. Relation to v0.3 Safe Activation
v0.2.5 creates the safety gate that v0.3 must pass before adding any install or activation flow. A future installer should refuse blocked profiles and require explicit confirmation for quirk-sensitive machines.
