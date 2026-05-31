# Microphone Repair Guide (Manual Verification)

## Core Rule
Route visibility is not proof of microphone functionality.

## Planning Command
```bash
pipetune repair mic-test-plan
```

## What the Plan Covers
- read-only route inspection commands
- optional manual capture test commands
- calibration safety notes

## Manual Capture Test Policy
- Recording is never automatic.
- Capture commands must be user-approved first.
- Generated audio files are local artifacts created only by manual user action.

## Calibration Note
Do not use built-in microphone for calibration until repeatable manual validation succeeds.
Prefer an external USB or dedicated measurement microphone.

## Privacy
PipeTune does not upload microphone or audit data.
