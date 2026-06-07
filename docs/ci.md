# Continuous Integration

PipeTune Linux uses GitHub Actions CI to verify every push and pull request before merging or tagging.

## CI jobs

| Job | Description |
|---|---|
| Python tests (3.11, 3.12) | Runs the full pytest suite on both supported Python versions |
| Packaging checks | Runs package inspect, build-check, smoke-test, and release check |
| CLI smoke check | Verifies the installed CLI entry point works |
| Artifact hygiene | Verifies no forbidden artifacts are staged or committed |
| Plugin validation | Validates LV2 TTL metadata and RT-safety analysis |

## Safe checks

All CI checks are non-mutating:

- No packages are uploaded to PyPI, COPR, Flatpak, or any registry.
- No LV2 plugin is installed globally.
- No audio routing is changed.
- No PipeWire, WirePlumber, ALSA, service, system, or user audio configuration is modified.

## Optional LV2 system dependencies

The plugin validation job installs system LV2 tools via `apt-get`:

```bash
sudo apt-get install -y gcc make lv2-dev lilv-utils
sudo apt-get install -y sord-validate || true
```

These are only needed for `lv2_validate`. The RT-safety check (`pipetune plugin validate --rt-safety`) is pure Python and requires no system packages. If `lv2_validate` is unavailable, the metadata validation will report it clearly.

### Ubuntu package note

The package name `sord` does not exist in the Ubuntu 24.04 (noble) repository used by GitHub Actions runners. The correct optional package for the `sord_validate` helper is `sord-validate`, which may or may not be available depending on the Ubuntu image version. CI installs it with `|| true` so that its absence does not fail the build. PipeTune treats a missing optional external validator helper as a warning while preserving all internal metadata checks.

## Why CI does not globally install plugins

PipeTune Linux does not auto-install LV2 plugins in CI because:

- CI runners are ephemeral and shared.
- Global installs in CI can mask missing local install steps.
- The plugin source and TTL metadata are validated directly without installing.

## Why CI does not route audio

Audio routing requires hardware or a running audio server (PipeWire/PulseAudio). CI runners do not have audio hardware, and routing audio in CI would be non-portable and unsafe for automated environments.

## Reproducing CI locally

All CI steps can be reproduced locally inside the project virtual environment:

```bash
source .venv/bin/activate
python -m pip install -e .[dev]
python -m pytest -q
pipetune version
pipetune package inspect
pipetune package build-check
pipetune package smoke-test
pipetune package artifact-check
pipetune release check
pipetune plugin validate --metadata
pipetune plugin validate --rt-safety
```

For LV2 metadata validation, install:

```bash
sudo apt-get install -y gcc make lv2-dev lilv-utils  # Debian/Ubuntu
sudo apt-get install -y sord-validate || true         # optional helper; may not exist on noble
sudo dnf install -y gcc make lv2-devel lilv-utils    # Fedora
```

## Fresh checkout smoke test

To verify PipeTune installs correctly from a clean checkout:

```bash
bash scripts/fresh-checkout-smoke.sh
```

This script:
1. Exports the current HEAD via `git archive` (only tracked files).
2. Creates a fresh virtual environment in a temp directory.
3. Installs PipeTune with `pip install -e .`.
4. Runs `pipetune version`, `pipetune package inspect`, `pipetune package smoke-test`, and both plugin validations.
5. Cleans up the temp directory on exit.
