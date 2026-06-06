# Profile Request Template

Use this template to request a new device profile for the PipeTune Linux profile database.

## Device Information

- **Device vendor:** (e.g., Sennheiser, Sony, Dell)
- **Device model:** (e.g., HD 650, WH-1000XM5, XPS 15 9500)
- **Profile type:** (headphone / laptop-speaker / microphone / bluetooth-device / measurement-correction)
- **Device category:** (e.g., over-ear, on-ear, in-ear, laptop, bluetooth, built-in)

## Source and License

- **Source type:** (autoeq-database / measured / generic-conservative / policy-note / other)
- **Source URL or reference:** (URL to measurement data, publication, or AutoEQ entry)
- **License:** (MIT / CC0 / CC-BY / other — must be compatible with project license)

## Quality Class

- [ ] A — Measured with documented equipment and reproducible method
- [ ] B — Derived from trusted open database (e.g., AutoEQ)
- [ ] C — Conservative generic safe profile
- [ ] D — Experimental / not installed by default

## Safety Notes

- Does this profile include EQ boosts above +6 dB? If yes, explain why this is safe.
- For laptop-speaker profiles: does the source data include high-pass filter (HPF) frequency?
- For laptop-speaker profiles: does the source data include limiter ceiling?

## Measurement Equipment (if measured)

- **Measurement microphone:** (model)
- **Measurement interface:** (model)
- **Measurement software:** (REW, ARTA, etc.)
- **Measurement method:** (free-field, diffuse-field, in-ear, other)

## Additional Context

- **OS and audio stack:** (e.g., Fedora 41, PipeWire 1.0)
- **Any known quirks or limitations:**

## Confirmation

- [ ] I have permission to share this measurement data under the stated license.
- [ ] I understand this request will be reviewed before any profile is added.
- [ ] I confirm this is not a request to auto-apply audio changes.
