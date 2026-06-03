# LV2 Safeguard Plugin

PipeTune v0.5.0 added the first local LV2 plugin foundation:

```text
plugins/lv2/pipetune-safeguard.lv2/
```

LV2 is a Linux audio plugin format used by hosts and audio routing systems. In PipeTune Linux, the LV2 work is a local build and validation foundation only. PipeTune does not install the plugin globally, auto-route audio through it, restart services, or modify PipeWire, WirePlumber, ALSA, system, service, or user audio configuration.

v0.5.1 is a hardening release. It improves local build checks, artifact hygiene, cleanup, metadata validation, RT-safety validation, and compiled-artifact validation when a local `.so` exists. It does not add new DSP features.

## Why A Safeguard Plugin

The first plugin is deliberately conservative. It is not an AI enhancer, spatializer, bass booster, or mastering suite. It is a safeguard chain:

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

The limiter is a simple hard safety limiter. It is intended to prevent output samples from exceeding the configured ceiling in offline validation. It is not a transparent mastering limiter and should not be described as improving sound. It does not do lookahead, release shaping, loudness optimization, saturation, or mastering-style gain management.

## Artifact Hygiene

Local build artifacts are ignored and should not be committed:

- `plugins/lv2/**/*.so`
- `plugins/lv2/**/*.o`
- `plugins/lv2/**/*.d`
- temporary plugin build files such as `*.tmp` and editor backup files

Source files are preserved by cleanup:

- `manifest.ttl`
- `pipetune-safeguard.ttl`
- `pipetune_safeguard.c`
- `Makefile`

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

The build artifact stays inside the local LV2 bundle:

```text
plugins/lv2/pipetune-safeguard.lv2/pipetune_safeguard.so
```

`pipetune plugin build --local` checks for `gcc`, `make`, and LV2 headers before building. If they are missing, it prints Fedora instructions but does not run `sudo`, install packages, or touch global LV2 directories.

The Makefile supports:

```bash
make -C plugins/lv2/pipetune-safeguard.lv2
make -C plugins/lv2/pipetune-safeguard.lv2 check
make -C plugins/lv2/pipetune-safeguard.lv2 clean
```

The Makefile intentionally refuses `make install`.

## Local Clean

Run:

```bash
pipetune plugin clean --local
```

Cleanup removes local build artifacts only from the repo LV2 bundle. It does not remove TTL metadata, C source, or the Makefile. It does not touch global LV2 directories and does not require root.

## Offline Validation

Run:

```bash
pipetune plugin validate --offline
```

Offline validation always validates the safety behavior using an offline reference implementation:

- limiter ceiling is respected
- preamp reduces gain
- high-pass attenuates low-frequency input compared with mid-frequency input
- bypass preserves input within tolerance
- no install or audio routing is performed

When `plugins/lv2/pipetune-safeguard.lv2/pipetune_safeguard.so` exists, validation also loads the compiled plugin directly, calls the LV2 descriptor, instantiates it, connects ports, runs synthetic buffers, and cleans up. The compiled checks cover limiter ceiling, preamp reduction, high-pass attenuation, bypass stereo preservation, and boundary/non-finite control values. If the `.so` is absent, PipeTune reports a warning and continues with reference validation instead of faking compiled validation.

## Metadata Validation

Run:

```bash
pipetune plugin validate --metadata
pipetune plugin validate --metadata --json
```

Metadata validation checks:

- `manifest.ttl` exists
- `pipetune-safeguard.ttl` exists
- plugin URI matches the CLI metadata and both TTL files
- audio and control ports are documented
- control ranges are documented:
  - `preamp_db`: `-24` to `0 dB`
  - `highpass_hz`: `60` to `250 Hz`
  - `limiter_ceiling_db`: `-12` to `-0.1 dB`
  - `bypass`: `0` to `1`

If `lv2_validate` is installed, PipeTune runs it against the TTL files. If `lv2_validate` is missing, metadata validation warns and explains the Fedora dependency path, but it does not fail automatically just because optional LV2 validation tooling is absent.

## RT-Safety Validation

Run:

```bash
pipetune plugin validate --rt-safety
```

The static RT-safety check inspects `pipetune_safeguard.c`, focuses on the LV2 `run()` processing callback path, strips comments before scanning, and rejects obvious non-real-time calls such as heap allocation, logging, file I/O, process spawning, sleep, and thread creation. It also verifies that unsafe or non-finite control values are clamped or handled safely.

This is a static trust check, not a formal proof. It is intentionally narrow and tuned to the conservative plugin scope.

## Current Limitations

- No GUI.
- No daemon.
- No automatic profile application.
- No global LV2 installation.
- No PipeWire/WirePlumber/ALSA routing integration.
- No subjective sound quality claims.
- Compiled validation is direct LV2 descriptor loading when the local `.so` exists; it is not a full host integration test.
- The high-pass filter is intentionally simple and conservative.
- The limiter is a hard safety limiter, not a mastering processor.
- `lv2_validate` remains optional, so machines without LV2 validation tooling can still run the built-in metadata checks.
