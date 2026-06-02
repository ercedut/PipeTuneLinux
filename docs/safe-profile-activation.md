# Safe Profile Activation

## 1. Purpose
PipeTune v0.3.0 installs generated PipeWire filter-chain configs into the user-level PipeWire configuration directory after safety preflight, explicit confirmation, backup, and manifest recording.

## 2. Why Activation Requires Preflight
Generated EQ files can be valid but still unsafe to install on the wrong machine or route. Preflight checks manifest metadata, profile type, gain safety, and hardware quirk status before installation.

## 3. User-Level Install Only
PipeTune installs only to:

```text
~/.config/pipewire/pipewire.conf.d/
```

It does not write to `/etc`, `/lib`, `/sys`, `/proc`, or system audio configuration.

## 4. Confirm Flags
Installation requires:

```bash
pipetune profile install <config> --user --confirm-install
```

Without both flags, PipeTune refuses to write files.

## 5. Hardware Quirk Confirmation
If preflight returns `requires_confirmation`, installation also requires:

```bash
--confirm-hardware-quirk
```

This confirms the user understands that physical output routing must be checked manually before restarting PipeWire.

## 6. Backup Behavior
If the destination config already exists, PipeTune backs it up under:

```text
~/.local/share/pipetune/backups/
```

Backup paths are recorded in the install manifest.

## 7. Manifest Behavior
Install manifests are stored under:

```text
~/.local/share/pipetune/installed-profiles/
```

They record install ID, profile name, source and destination paths, checksums, preflight status, backup path, and rollback status.

## 8. Manual Restart Requirement
PipeTune does not restart services. After a real install, it prints:

```bash
systemctl --user restart pipewire pipewire-pulse wireplumber
```

The user decides whether and when to run it.

## 9. Rollback Behavior
Rollback removes only PipeTune-owned installed config files whose paths and checksums match the install manifest. If a backup exists, it is restored. Rollback logs are stored under `~/.local/share/pipetune/rollback-log/`.

## 10. What v0.3.0 Does Not Do
- Does not use sudo.
- Does not install system-level configuration.
- Does not restart audio services.
- Does not auto-switch profiles.
- Does not create daemons or GUI.
- Does not install blocked or unknown preflight profiles.

## 11. Examples
Dry run:

```bash
pipetune profile dry-run-install generated/sennheiser-hd-650.filter-chain.conf --user
```

Install on normal machine:

```bash
pipetune profile install generated/sennheiser-hd-650.filter-chain.conf --user --confirm-install
```

Install on HDA quirk machine:

```bash
pipetune profile install generated/sennheiser-hd-650.filter-chain.conf --user --confirm-install --confirm-hardware-quirk
```

Rollback latest install:

```bash
pipetune profile rollback --latest --confirm-rollback
```
