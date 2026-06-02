# Measurement and Calibration

PipeTune v0.4.1 provides a local, read-only measurement foundation with stricter inspection and validation. It creates files and reports only. It does not modify PipeWire, WirePlumber, ALSA, system audio configuration, user audio configuration, or restart audio services.

v0.4.1 does not improve sound directly. It improves measurement trustworthiness before any later plugin, daemon, or automatic correction work.

## Log Sweep Generation
Use `generate-sweep` to create a mono logarithmic sine sweep WAV:

```bash
pipetune measure generate-sweep \
  --output measurements/sweeps/log-sweep-48k.wav \
  --duration 10 \
  --sample-rate 48000 \
  --start-hz 20 \
  --end-hz 20000 \
  --amplitude 0.5
```

The command also writes a sidecar JSON file with sample rate, duration, frequency range, amplitude, PipeTune version, timestamp, and a safe playback warning.

Keep playback volume low. Start quiet, increase slowly, and stop immediately if the speaker, headphones, or listener is stressed. PipeTune refuses sweep amplitude above `0.9`, but output loudness also depends on your player, mixer, amplifier, and device.

## Built-In Microphones Are Approximate
Built-in laptop microphones are not calibrated measurement microphones. They often have their own EQ, noise suppression, placement effects, enclosure resonances, and limited low-frequency accuracy.

PipeTune therefore treats built-in microphone measurements as approximate. Reports and correction drafts must not be read as proof of sound quality improvement.

## Sweep Analysis
Use `analyze-sweep` after recording playback of a generated sweep:

```bash
pipetune measure analyze-sweep \
  --sweep measurements/sweeps/log-sweep-48k.wav \
  --recorded measurements/recordings/laptop-speaker-recorded.wav \
  --output measurements/reports/laptop-speaker-response.json \
  --csv-output measurements/reports/laptop-speaker-response.csv
```

The command validates WAV data, checks sample-rate compatibility, estimates peak and RMS level, detects clipping, and writes an approximate FFT-based frequency response.

If clipping is detected, the report quality is `fail`. If the recording is too quiet, the report quality is `warn` or `fail` depending on level. Lower playback or capture gain for clipping. Raise level carefully for quiet recordings.

This command does not generate correction automatically.

## WAV Inspection
Use `inspect-wav` to check a WAV before trusting it:

```bash
pipetune measure inspect-wav --input measurements/recordings/laptop-speaker-recorded.wav
pipetune measure inspect-wav --input measurements/recordings/laptop-speaker-recorded.wav --json
```

The command reports measured sample rate, duration, channels, sample format, peak, RMS, clipping, silence, DC offset, dominant frequency estimate, quality flags, and a `pass`, `warn`, or `fail` verdict. It does not write files.

Clipping and silence matter because either condition can make frequency response data unreliable. Clipped recordings should be repeated at lower playback or capture gain. Silent or very quiet recordings should be repeated with careful gain staging.

## REW Import Workflow
Room EQ Wizard and similar tools can export CSV response data. PipeTune accepts common frequency and magnitude column names:

- `Frequency`
- `Freq`
- `Hz`
- `SPL`
- `Magnitude`
- `dB`

Example:

```bash
pipetune measure import-rew \
  --input measurements/rew/export.csv \
  --output measurements/imported/rew-normalized.csv
```

The normalized output columns are:

```text
freq_hz,magnitude_db
```

A sidecar JSON records source format, row count, skipped row count, detected source columns, frequency range, import timestamp, and warnings.

## Response Validation
Use `validate-response` before comparison or correction:

```bash
pipetune measure validate-response \
  --input measurements/imported/rew-normalized.csv
```

Validation checks positive frequencies, sorted or unsorted frequency data, duplicate frequencies, unrealistic magnitudes, too few points, narrow frequency coverage, and large adjacent magnitude jumps. Output is `pass`, `warn`, or `fail`.

## Response Comparison
Use `compare-response` to compare normalized before/after CSV files:

```bash
pipetune measure compare-response \
  --before measurements/before.csv \
  --after measurements/after.csv \
  --output measurements/reports/response-comparison.json
```

PipeTune interpolates onto a shared frequency grid when needed and reports average absolute difference, maximum absolute difference, low/mid/high band summaries, and `flatter_by_variance`.

The wording is deliberately limited. `flatter_by_variance: true` means only that the after response has lower variance by this simple metric. It does not mean better sound or subjective improvement.

## Correction Draft Workflow
Use `generate-correction` to create a conservative draft from normalized response data:

```bash
pipetune measure generate-correction \
  --input measurements/imported/rew-normalized.csv \
  --output profiles/speakers/laptop-correction-draft.toml \
  --target flat \
  --safe
```

The output is a draft TOML profile. It is not active. It is not installed. It is not applied.

Safety limits include:

- `--safe` is required.
- Maximum boost is `+3 dB`.
- Laptop-speaker mode includes high-pass metadata.
- Laptop-speaker mode does not boost below `120 Hz`.
- Preamp headroom metadata is included.
- Limiter metadata is included where compatible.
- Corrections are broad-band and limited to a small number of EQ bands.

If a response would require unsafe boost, PipeTune refuses to generate the draft.

v0.4.1 also refuses correction drafts when response validation fails because of too few points, narrow coverage, unrealistic magnitude values, or unrealistic magnitude jumps. A correction safety report JSON is written next to successful draft TOML output.

## Why Profiles Are Not Auto-Applied
Measurements can be wrong because of microphone calibration, placement, room reflections, playback gain, capture gain, clipping, background noise, or export mistakes.

For that reason, PipeTune v0.4.1 only creates reports and draft correction data. Users must review, remeasure, and explicitly use the existing profile safety and activation workflow before any manual use.

See `docs/measurement-report-fields.md` for stable machine-readable report fields.
