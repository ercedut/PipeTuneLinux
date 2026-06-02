# Microphone Verification in PipeTune v0.2.4

## 1. Purpose
Provide explicit, user-approved microphone verification without automatically changing system configuration.

## 2. Why Route Visibility Is Not Enough
A visible default source only proves route visibility. It does not prove real capture signal quality or functionality.

## 3. Privacy Model
- Recording is never automatic.
- Recording requires `--confirm-recording`.
- Generated WAV/JSON files are local-only and gitignored.
- PipeTune does not upload recordings.

## 4. Commands
```bash
pipetune verify mic-plan
pipetune verify mic-capture --duration 5 --confirm-recording
pipetune verify mic-analyze <wav_file>
pipetune verify mic-status
pipetune hardware gain-audit
```

## 5. How to Run a Safe Capture Test
1. Run `pipetune hardware mic-audit`.
2. Run `pipetune verify mic-capture --duration 5 --confirm-recording --analyze`.
3. Speak clearly during capture.
4. Review analysis locally.

## 6. How to Analyze a WAV File
Use:
```bash
pipetune verify mic-analyze verification/microphone/mic-test-YYYYMMDD-HHMMSS.wav
```

## 7. How to Interpret Results
- `signal_detected`: a usable signal was detected; document current gain state before persistence.
- `silence_likely`: weak or near-silent signal; if a previous test clipped, inspect ALSA gain staging before assuming a dead microphone.
- `clipping_detected`: signal clipping was detected; lower ALSA Capture, Mic Boost, or Digital gain before lowering only Pulse volume.
- `invalid_file`: WAV could not be parsed safely.

This is not calibration-grade quality scoring.

## 8. Capture Gain Audit
Use `pipetune hardware gain-audit` to inspect current gain state without modifying anything. The audit is local and may show device-specific mixer names, so review output before sharing publicly.

## 9. What PipeTune Does Not Do
- Does not fix microphone routing automatically.
- Does not restart audio services.
- Does not edit ALSA/PipeWire/WirePlumber configuration.
- Does not change Capture, Mic Boost, Digital, or Pulse/PipeWire volume automatically.
- Does not run `sudo alsactl store`.

## 10. How This Helps Future HDA/Mic Repair
It provides explicit evidence for route validation before manual repair decisions in HDA/UCM/WirePlumber workflows.
