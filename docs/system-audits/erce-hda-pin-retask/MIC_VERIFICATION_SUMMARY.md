# Microphone Verification Summary

## Result

The internal microphone route is functional after capture gain tuning.

Latest successful PipeTune verification:

- Peak normalized: 0.235
- RMS normalized: 0.011
- Clipping detected: no
- Silence likely: no
- Status: signal_detected

## Interpretation

The microphone is not completely broken. The earlier failure pattern was caused by gain staging / capture level behavior rather than total capture-path failure.

At high input levels, the microphone clipped.
At lower Pulse/PipeWire volume levels, the captured signal became silent.
A working range was found by adjusting ALSA capture-side controls.

## Safety note

This result does not make the built-in microphone calibration-grade. It only proves that the selected capture route can record a real signal.

For future calibration or measurement features, an external USB or measurement microphone is still preferred.

## PipeTune impact

Future PipeTune versions should distinguish:

- route visible
- capture successful
- signal detected
- clipping detected
- silence likely
- calibration-grade measurement

No system configuration was modified by PipeTune.
