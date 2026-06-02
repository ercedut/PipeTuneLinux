# LV2 Safeguard Plugin

PipeTune v0.5.0 adds the first local LV2 plugin foundation:

```text
plugins/lv2/pipetune-safeguard.lv2/
```

LV2 is a Linux audio plugin format used by hosts and audio routing systems. In PipeTune Linux, the v0.5.0 LV2 work is a local build and offline validation foundation only. PipeTune does not install the plugin globally, auto-route audio through it, restart services, or modify PipeWire, WirePlumber, ALSA, system, service, or user audio configuration.

## Why A Safeguard Plugin

The first plugin is deliberately boring. It is not an AI enhancer, spatializer, bass booster, or mastering suite. It is a conservative safeguard chain:

- preamp/headroom gain
- mandatory high-pass filter
- hard safety limiter
- bypass control

Real-time safety matters more than impressive features. The plugin code avoids heap allocation, file I/O, logging, dynamic allocation, and system calls inside the LV2 audio `run()` callback.

## Why Bass Boost Is Dangerous

Laptop speakers are small, excursion-limited, and often already protected by vendor DSP. Low-frequency boost can drive distortion, mechanical stress, heat, and audible failure modes quickly. Built-in microphones are also approximate and uncalibrated, so a measurement suggesting weak bass is not proof that bass boost is safe.

For laptop-speaker safety, PipeTune treats high-pass filtering as mandatory and low-frequency boost as unsafe by default.

## Controls

- `preamp_db`
  - default: `-6.0 dB`
  - safe range: `-24.0 dB` to `0.0 dB`
- `highpass_hz`
  - default: `120 Hz`
  - safe range: `60 Hz` to `250 Hz`
- `limiter_ceiling_db`
  - default: `-1.0 dB`
  - safe range: `-12.0 dB` to `-0.1 dB`
- `bypass`
  - default: `0`
  - range: `0` to `1`

Unsafe or missing control values are clamped to safe defaults/ranges.

## Limiter Model

The v0.5.0 limiter is a simple hard safety limiter. It is intended to prevent output samples from exceeding the configured ceiling in offline validation. It is not a transparent mastering limiter and should not be described as improving sound.

## Local Build

Fedora build dependencies:

```bash
sudo dnf install gcc make lv2-devel
```

PipeTune never runs this command automatically.

Build locally:

```bash
pipetune plugin build --local
```

Equivalent direct command:

```bash
make -C plugins/lv2/pipetune-safeguard.lv2
```

The build artifact stays inside the local LV2 bundle. The Makefile intentionally refuses `make install`.

## Offline Validation

Run:

```bash
pipetune plugin validate --offline
```

v0.5.0 validates the safety behavior using an offline reference implementation:

- limiter ceiling is respected
- preamp reduces gain
- high-pass attenuates low-frequency input compared with mid-frequency input
- bypass preserves input within tolerance
- no install or audio routing is performed

The tests also verify that the LV2 source files, manifest, TTL metadata, Makefile, documented build command, and control ranges exist.

## Current Limitations

- No GUI.
- No daemon.
- No automatic profile application.
- No global LV2 installation.
- No PipeWire/WirePlumber/ALSA routing integration.
- No subjective sound quality claims.
- Offline validation is reference-level plus build-level artifact checking; it is not a full host integration test.
- The high-pass filter is intentionally simple and conservative.
- The limiter is a hard safety limiter, not a mastering processor.

