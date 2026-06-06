# Bluetooth Policy Diagnostics

PipeTune v0.8.1 adds `pipetune bluetooth policy-audit`, a read-only diagnostic command for Bluetooth audio devices. It detects Bluetooth devices, their active profile (A2DP vs HSP/HFP), and codec hints if available.

## Command

```bash
pipetune bluetooth policy-audit
pipetune bluetooth policy-audit --json
```

## What It Reports

- Bluetooth device availability (detected/not detected/unknown)
- Detected Bluetooth device names (from wpctl status output)
- Active profile if detectable: A2DP, HSP/HFP, or unknown
- Codec hint if parseable (SBC, AAC, aptX, LDAC, etc.)
- HFP/HSP warning if music-quality degradation is suspected
- A2DP OK confirmation if A2DP is detected
- Final verdict: pass/warn/fail

## Bluetooth Profile: Why It Matters

Bluetooth headsets support multiple audio profiles:

**HSP/HFP (Headset/Hands-Free Profile):**
- Designed for voice calls.
- Uses a narrow codec: 8kHz (HSP) or 16kHz (HFP/mSBC).
- When a Bluetooth headset is used for music in HSP/HFP mode, audio quality is significantly degraded — this is voice-call quality, not music quality.

**A2DP (Advanced Audio Distribution Profile):**
- Designed for music and media playback.
- Uses wideband stereo codecs: SBC, AAC, aptX, LDAC, LC3, etc.
- This is the preferred profile for music and general listening.

If `pipetune bluetooth policy-audit` warns about HSP/HFP, your Bluetooth headset is in voice-call mode. Switch to A2DP for better music quality.

## Why Bluetooth Profile Is Not Switched Automatically

PipeTune does not switch Bluetooth profiles automatically because:
1. The current active profile may be intentional (e.g., a voice call in progress).
2. Switching profiles while audio is playing can cause glitches.
3. The correct target profile depends on the use case and device capabilities.

To switch manually:
```bash
pactl list cards  # find the Bluetooth card ID and profile names
pactl set-card-profile <card-id> <profile-name>
```

Or use a Bluetooth manager application (e.g., KDE's audio settings, GNOME Bluetooth).

WirePlumber rule generation to automate profile selection is in the roadmap (v0.8.1 previews only).

## JSON Output Schema

```json
{
  "command": "bluetooth policy-audit",
  "pipetune_version": "0.8.1",
  "collected_at": "2026-06-06T12:00:00+00:00",
  "host": "hostname",
  "verdict": "warn",
  "passed": true,
  "hfp_hsp_suspected": true,
  "a2dp_ok": false,
  "active_profile": "HSP/HFP",
  "codec": "",
  "devices_detected": ["Sony WH-1000XM4 (HSP/HFP)"],
  "safety": {
    "read_only": true,
    "modified_system": false,
    "restarted_services": false,
    "changed_routing": false,
    "changed_bluetooth_profile": false
  }
}
```

## Limitations

- Profile detection is best-effort based on `wpctl status` text output.
- If `wpctl` is not available, Bluetooth status will be reported as unknown.
- Codec detection relies on text patterns in `wpctl` and `pactl` output.
- Some devices may not report profile names clearly in output.

## Safety

This command is fully read-only:
- No Bluetooth profile is changed.
- No system configuration is modified.
- No service is restarted.
- No audio routing is changed.
