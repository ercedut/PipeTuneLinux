# Install PipeTune Linux

PipeTune Linux is installed as a Python CLI. Normal verification does not require root and does not modify PipeWire, WirePlumber, ALSA, service files, system config, or user audio config.

## Fresh Checkout

```bash
git clone <repo-url>
cd PipeTuneLinux
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Verify the installed command:

```bash
pipetune version
pipetune doctor
pipetune package inspect
```

`pipetune doctor` reads local system audio state for diagnostics. It does not change audio configuration.

## Optional LV2 Plugin Build Dependencies

The LV2 safeguard plugin can be built locally from the repository bundle. On Fedora, install optional build and validation tools manually:

```bash
sudo dnf install gcc make lv2-devel lilv
```

PipeTune never runs this command automatically.

Build the local plugin artifact:

```bash
pipetune plugin build --local
```

Clean local plugin artifacts:

```bash
pipetune plugin clean --local
```

The plugin is not globally installed and is not routed into PipeWire automatically.

## Package Verification

```bash
pipetune package inspect
pipetune package build-check
pipetune package smoke-test
```

If `pipetune package build-check` reports that the optional Python build module is missing, install it manually:

```bash
python -m pip install build
```

Build artifacts are local and ignored under `dist/`.

## Uninstall Editable Package

```bash
pip uninstall pipetune-linux
```

Uninstalling the Python package does not remove user-created reports, generated profiles, or local repository files.

## Safety Boundaries

PipeTune does not automatically alter PipeWire routing, install LV2 plugins globally, restart services, add daemons, or apply profiles. Commands that can write user-level PipeWire profile files require explicit confirmation in their own workflows.
