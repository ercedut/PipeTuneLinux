# PUBLIC SUMMARY

## Privacy Statement
This summary is sanitized for repository sharing.
Raw audit files are local-only, stored under `raw/`, and gitignored by default.
PipeTune does not send audit data anywhere.

## Technical Finding
- Manual HDA retask status: detected
- Built-in mic route visibility: yes
- Capture test performed: no

## Next Manual Steps
- Confirm speaker/headphone behavior manually before any profile application.
- Review `FIX_PLAN.md` and local `raw/` data before manual system changes.
- Use an external microphone for calibration workflows until built-in mic is validated.

## What Was Not Modified
- No system audio configuration was modified.
- No HDA pin override was written.
- No PipeWire/WirePlumber/ALSA restart was performed.

Public files: docs/system-audits/<user>-hda-pin-retask/README.md, docs/system-audits/<user>-hda-pin-retask/PUBLIC_SUMMARY.md, docs/system-audits/<user>-hda-pin-retask/FIX_PLAN.md
Local raw directory: docs/system-audits/<user>-hda-pin-retask/raw
