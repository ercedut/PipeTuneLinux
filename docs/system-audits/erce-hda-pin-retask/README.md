# HDA Pin Retask Audit Case Study (Sanitized)

## 1. Summary
This is a sanitized public-facing case study for a hardware audio quirk machine.
Raw machine audit files are stored under `raw/` locally and intentionally gitignored.

## 2. Observed Historical Behavior
- This machine has suspected manual HDA pin retask/routing quirk behavior.
- Speaker output currently works and must not be broken.
- Built-in microphone route is visible but not proven functional.
- Capture test has not been performed.

## 3. Current PipeTune Interpretation
- Hardware quirk status: detected.
- Do not auto-apply speaker/headphone profiles without manual output confirmation.
- Built-in microphone should be treated as unreliable until manual capture verification is completed.

## 4. Why This Is Not a DSP Problem
- The issue pattern is consistent with HDA codec pin routing and route policy behavior.
- EQ/DSP profile generation cannot correct hardware pin assignment mismatches.

## 5. Risk for Future PipeTune Features
- Future profile logic must include hardware-quirk metadata guardrails.
- Automatic route assumptions are unsafe on this machine class.

## 6. Safe Rules for This Machine
- Keep all commands read-only by default.
- Do not auto-apply output profiles without manual confirmation.
- Do not use built-in microphone as a calibration source.
- Prefer external USB or measurement microphones for calibration workflows.

## 7. Collected Files
- Public README: docs/system-audits/<user>-hda-pin-retask/README.md
- Public summary: docs/system-audits/<user>-hda-pin-retask/PUBLIC_SUMMARY.md
- Repair plan: docs/system-audits/<user>-hda-pin-retask/FIX_PLAN.md
- Local raw audit directory: docs/system-audits/<user>-hda-pin-retask/raw

## 8. Next Diagnostic Steps
- Review `FIX_PLAN.md` before any manual state-changing action.
- Review local `raw/` captures before sharing anything externally.
- Run manual speaker/headphone and mic verification outside PipeTune when approved.
