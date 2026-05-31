# HDA Pin Retask and Internal Microphone Repair Plan

## 1. Current Known State
- Speaker output currently works with historical/manual retask context.
- Headphone auto-switch behavior may still be unreliable.
- Built-in internal microphone route is visible but not proven functional without capture test.

## 2. What Must Not Be Broken
- Do not break current speaker output.
- Do not erase or overwrite existing manual retask state blindly.
- Do not assume built-in mic is valid for calibration.

## 3. Likely Root Causes
- HDA codec pin assignment mismatch (speaker/headphone routing quirk).
- Persisted retask override interactions with ALSA/UCM profile selection.
- WirePlumber/PipeWire route selection exposing unstable source/sink defaults.

## 4. Read-Only Checks Already Collected
- ALSA/PipeWire command snapshots (`pactl`, `wpctl`, `aplay`, `arecord`) in local `raw/`.
- `/proc/asound` snapshots and codec file copies when readable.
- HDA pin config visibility (`init_pin_configs`, `driver_pin_configs`, `user_pin_configs`).
- Retask-reference search under `/etc/modprobe.d` and `/lib/firmware`.

## 5. Manual Verification Checklist
- Confirm speaker output path still works.
- Confirm headphone insertion/removal switching behavior.
- Confirm source mute/state/default source values.
- Confirm whether internal mic route appears and can capture signal.

## 6. Safe Repair Strategy
- Keep all current working state intact until backups are complete.
- Perform only one manual change at a time.
- After each change, re-run read-only audit and manual output checks.
- Stop immediately if speaker route regresses.

## 7. hdajackretask Investigation Path
- MANUAL / DO NOT RUN WITHOUT CONFIRMATION: Open `hdajackretask` for inspection only.
- MANUAL / DO NOT RUN WITHOUT CONFIRMATION: Check whether any boot override is currently enabled.
- MANUAL / DO NOT RUN WITHOUT CONFIRMATION: Back up `/etc/modprobe.d/hda-jack-retask.conf` if present.
- MANUAL / DO NOT RUN WITHOUT CONFIRMATION: Back up `/lib/firmware/hda-jack-retask.fw` if present.
- Do not apply new retask pins until speaker/headphone mapping is documented first.

## 8. ALSA UCM Investigation Path
- Read-only: inspect available UCM2 profile definitions for this codec/card.
- Read-only: compare capture/playback controls exposed before/after manual tests.
- If UCM mapping conflicts are found, plan controlled manual adjustments with rollback notes first.

## 9. WirePlumber/PipeWire Route Investigation Path
- Read-only: verify default sink/source consistency from `pactl` and `wpctl` outputs.
- Read-only: inspect route visibility and profile mode transitions during jack events.
- Avoid policy changes until hardware pin behavior is confirmed stable.

## 10. Built-in Microphone Investigation Path
- Read-only first: confirm internal mic source names and states.
- MANUAL / DO NOT RUN WITHOUT CONFIRMATION: perform short user-approved capture test outside PipeTune.
- If internal mic remains broken, treat built-in mic as unreliable for calibration.

## 11. Rollback Strategy
- Keep backups of any retask-related files before changing them.
- Maintain a chronological change log with timestamped audit outputs.
- If regression occurs, restore last known-good manual retask configuration.

## 12. When to Stop
- Stop when speaker routing regresses.
- Stop when behavior becomes non-deterministic after a change.
- Stop and escalate to controlled manual hardware debug if internal mic remains unavailable after safe checks.
