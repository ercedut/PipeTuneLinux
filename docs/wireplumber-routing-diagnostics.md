# WirePlumber and Routing Diagnostics

PipeTune v0.8.0 adds read-only diagnostics for WirePlumber, PipeWire routing state, default devices, and route analysis. All commands are read-only: nothing is modified, no services are restarted, and no routing is changed.

## What These Commands Do

### pipetune wireplumber audit

Checks the status of WirePlumber, PipeWire, and pipewire-pulse services (via `systemctl --user is-active`), then collects default sink/source names, detected card/sink/source counts, and Bluetooth profile if detectable.

```bash
pipetune wireplumber audit
pipetune wireplumber audit --json
```

Reports:
- WirePlumber active/inactive/unknown
- PipeWire active/inactive/unknown
- pipewire-pulse active/inactive/unknown
- Default sink and source
- Detected card, sink, source counts
- Bluetooth HFP/HSP warning or A2DP OK if Bluetooth is present
- Final verdict: pass/warn/fail

### pipetune route audit

Analyzes default output/input routes, detects virtual filter-chain sinks, PipeTune configs, and Bluetooth profile mismatches.

```bash
pipetune route audit
pipetune route audit --json
```

Reports:
- Default output route (sink)
- Default input route (source)
- Sink and source counts
- Whether virtual filter-chain sinks exist
- Whether PipeTune-related configs appear active
- Bluetooth HFP/HSP music warning if detected
- Final verdict: pass/warn/fail

### pipetune route explain

Gives a plain-English explanation of PipeWire routing concepts.

```bash
pipetune route explain
pipetune route explain --json
```

Explains:
- The signal path: App → pipewire-pulse → PipeWire → WirePlumber → device
- What default sink and source mean
- What WirePlumber and pipewire-pulse do
- Why Bluetooth profile matters (A2DP vs HSP/HFP)
- What virtual filter-chain sinks are
- Why this command is read-only

## Key Concepts

### WirePlumber

WirePlumber is the session and policy manager for PipeWire. It decides:
- Which device is the default sink/source
- How Bluetooth profiles are selected (A2DP vs HFP/HSP)
- How virtual devices (filter-chains) are connected

PipeTune does not modify WirePlumber configuration in this release.

### PipeWire

PipeWire is the audio server that routes audio between applications and hardware. It replaces PulseAudio and JACK for most Linux desktop audio.

### pipewire-pulse

A PulseAudio-compatibility layer inside PipeWire. Applications using the PulseAudio API are served through this layer without modification.

### Default Sink and Source

The default sink is the audio output device that PipeWire routes playback to when an application does not request a specific device. The default source is the audio input used for recording.

### Bluetooth Profile: Why It Matters

Bluetooth headsets support multiple profiles:

**HSP/HFP (Headset/Hands-Free Profile):** Designed for voice calls. Uses narrow 8kHz or 16kHz codecs. When a Bluetooth headset is used for music in HSP/HFP mode, audio quality is degraded — voice-call quality only.

**A2DP (Advanced Audio Distribution Profile):** Designed for music. Uses wideband stereo codecs (SBC, AAC, aptX, LDAC). This is the preferred profile for music playback.

If `pipetune wireplumber audit` warns about HSP/HFP, the Bluetooth device is in voice-call mode. Switching to A2DP is typically done through WirePlumber policy or manually via `pactl set-card-profile` — PipeTune does not do this automatically in v0.8.0.

## What This Release Does NOT Do

- Does not generate WirePlumber rules (planned for v0.8.1).
- Does not install WirePlumber config.
- Does not call `wpctl set-default` or change the default device.
- Does not call `pactl set-card-profile` or switch Bluetooth profiles.
- Does not restart PipeWire, WirePlumber, or pipewire-pulse.
- Does not modify any system, user, or audio configuration.

## JSON Output Format

All audit commands support `--json` for machine-readable output. The JSON schema includes:

```json
{
  "command": "wireplumber audit",
  "pipetune_version": "0.8.0",
  "collected_at": "2026-06-06T12:00:00+00:00",
  "host": "hostname",
  "verdict": "pass",
  "checks": [...],
  "warnings": [...],
  "errors": [...],
  "safety": {
    "read_only": true,
    "modified_system": false,
    "restarted_services": false,
    "changed_routing": false
  }
}
```

The `safety` block is always present and always confirms the command is read-only.

## CI and Testing

CI does not require live WirePlumber or PipeWire. All tests use fixture text files in `tests/fixtures/wireplumber/` for parse/render behavior. Service status checks are mocked in tests.

See `docs/ci.md` for CI job details.

## Limitations

- Diagnostics depend on `systemctl --user`, `wpctl`, and `pactl`. If these tools are not installed or not available in CI, output will include "unavailable" warnings.
- Bluetooth profile detection is best-effort: profile names are parsed from `wpctl status` text output, which may not always be complete.
- WirePlumber rule suggestion and preview is deferred to v0.8.1.
