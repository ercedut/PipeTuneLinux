# Microphone Repair Guide (Manual Verification)

## Core Rule
Route visibility is not proof of microphone functionality.

## Planning Command
```bash
pipetune repair mic-test-plan
pipetune verify mic-plan
pipetune hardware gain-audit
pipetune repair gain-plan
pipetune repair gain-matrix
```

## What the Plan Covers
- read-only route inspection commands
- optional manual capture test commands
- calibration safety notes
- read-only gain state audit
- manual gain tuning sequence and test matrix

## Manual Capture Test Policy
- Recording is never automatic.
- Capture commands must be user-approved first.
- Generated audio files are local artifacts created only by manual user action.
- Prefer `pipetune verify mic-capture --duration 5 --confirm-recording --analyze` for explicit workflow.

## Calibration Note
Do not use built-in microphone for calibration until repeatable manual validation succeeds.
Prefer an external USB or dedicated measurement microphone.

## Gain Staging Note
Clipping at high Pulse/PipeWire volume and silence after lowering it can both point to ALSA-side gain staging, selected capture source behavior, or HDA quirk interaction. Use `pipetune hardware gain-audit` first, then tune manually one stage at a time.

PipeTune may print example commands such as `amixer -c 0 set 'Capture' 60% cap`, but it does not execute them. Do not run `sudo alsactl store` until stable non-clipping values are confirmed and documented.

## Privacy
PipeTune does not upload microphone or audit data.
Do not upload raw microphone WAV files to public issues; share summarized analysis when possible.
Mixer state can reveal hardware details; review raw audit output before sharing publicly.
