# Fedora KDE Setup Notes

PipeTune Linux targets Fedora KDE 44+ and modern Linux systems using PipeWire + WirePlumber.

## Optional package setup
```bash
sudo dnf install -y pipewire pipewire-pulseaudio pipewire-alsa wireplumber alsa-utils pavucontrol easyeffects
```

## Important behavior in v0.1
- v0.1 does not require EasyEffects.
- v0.1 does not modify system configuration.
- v0.1 does not require `sudo` to run.

## Minimal runtime expectation
- PipeWire installed and active in the user session.
- WirePlumber installed and active in the user session.
- ALSA utilities available for richer diagnostics (`aplay`, `arecord`).
