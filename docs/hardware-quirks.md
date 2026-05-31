# Hardware Audio Quirks in PipeTune

## What Is a Hardware Audio Quirk?
A hardware audio quirk is a machine-specific behavior where normal Linux audio stack assumptions are unsafe.
Examples include HDA pin-routing mismatches, manual codec retask overrides, or unreliable jack/microphone signaling.

## HDA Pin Retasking
HDA pin retasking changes codec pin behavior (for example, speaker/headphone mapping).
On quirk machines, this may be required to restore speaker output, but it can destabilize other routes such as headphone auto-switching or internal mic capture.

## Why Speaker/Headphone Route Detection Can Be Unsafe
If a machine has historical manual retask changes, automatic assumptions about output routes can break working paths.
PipeTune must surface this risk and require manual confirmation before any future profile activation logic touches output targeting.

## Why Built-in Microphone Cannot Be Trusted for Calibration When Broken
If internal mic routing is unreliable, calibration and measurements become invalid.
On quirk machines, use external USB or dedicated measurement microphones for future calibration workflows.

## How PipeTune Should Treat Quirk Machines
- Treat hardware state as potentially fragile.
- Keep commands read-only unless user explicitly runs manual repair actions outside PipeTune.
- Block or warn before any future auto-activation behavior that depends on reliable route assumptions.

## Privacy and Sharing
- Raw hardware audit captures are local-only and stored under `docs/system-audits/.../raw/`.
- Raw captures may include machine-specific details and are gitignored by default.
- Public Markdown summaries are sanitized before sharing.
- PipeTune does not upload audit data anywhere.
- Microphone capture tests are manual-only and never triggered automatically.

## Future Profile Metadata
```toml
[hardware]
quirk = true
quirk_type = "manual_hda_pin_retask"
auto_switch_safe = false
built_in_microphone_reliable = false
requires_manual_output_confirmation = true
```

This metadata model is a forward-compatible guardrail for v0.3+ profile logic.
