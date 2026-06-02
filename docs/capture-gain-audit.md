# Capture Gain Audit

## 1. Purpose
PipeTune v0.2.4 adds a read-only capture gain audit for microphone gain staging. It helps explain clipping, silence, and usable signal results without changing mixer or system settings.

## 2. Why Microphone Route Visibility Is Not Enough
A visible Pulse/PipeWire source or ALSA capture device only proves that a route exists. It does not prove that the selected source, ALSA Capture, Mic Boost, Digital gain, and Pulse/PipeWire volume are staged correctly.

## 3. Why Clipping and Silence Can Both Happen
Clipping can happen when an early gain stage is too hot. Lowering only Pulse/PipeWire source volume may not fix clipping that already occurred earlier in the chain.

Silence can happen when the wrong stage is lowered, when the selected capture source changes behavior, or when an ALSA-side control has a threshold effect. If a previous test clipped and a later test is silent, treat that as gain-staging evidence, not proof that the microphone is dead.

## 4. Pulse/PipeWire Volume vs ALSA Capture vs Mic Boost vs Digital Gain
- Pulse/PipeWire source volume is the session-level source volume.
- ALSA Capture controls the hardware capture gain where available.
- Mic Boost or Internal Mic Boost adds pre-capture amplification and can cause clipping.
- Digital gain can add extra gain after analog capture and can also contribute to clipping.
- Input Source controls may select which physical or logical capture path is active.

## 5. Safe Tuning Sequence
1. Run `pipetune hardware gain-audit`.
2. Keep Pulse/PipeWire source volume around a reference level such as 80%.
3. Lower ALSA Mic Boost first.
4. Lower ALSA Capture if clipping continues.
5. Keep Digital gain low initially.
6. Test with `pipetune verify mic-capture --duration 5 --confirm-recording --analyze`.
7. If silence occurs, raise ALSA Capture gradually before increasing Mic Boost.
8. Use Mic Boost only after Capture alone fails to produce useful signal.

## 6. Manual Test Matrix
Use `pipetune repair gain-matrix` to print a structured baseline matrix. For each row, run:

```bash
pipetune verify mic-capture --duration 5 --confirm-recording --analyze
```

Target:
- Peak normalized: 0.200-0.800
- RMS normalized: 0.010-0.150
- Clipping detected: no
- Silence likely: no
- Status: signal_detected

## 7. Persistence Warning
Do not run `sudo alsactl store` until a stable non-clipping baseline is found. If persistence is desired later, document the exact stable Pulse/PipeWire, Capture, Mic Boost, Digital, and Input Source values first.

## 8. What PipeTune Does Not Do
- Does not use sudo.
- Does not modify ALSA, PipeWire, WirePlumber, HDA, or system configuration.
- Does not run `amixer set`, `pactl set-source-volume`, or `alsactl store`.
- Does not restart audio services.
- Does not record audio unless `--confirm-recording` is explicitly used.
- Does not upload audio recordings or mixer audits.
- Does not write gain audit reports by default.

Gain audits are local. Generated recordings remain ignored. Mixer state can reveal device details, so raw outputs should not be shared publicly without review.
