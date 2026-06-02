# Profile Rollback

## 1. Purpose
Rollback reverses a PipeTune-installed user-level profile without touching arbitrary user files or system configuration.

## 2. Install Manifest
Rollback uses the install manifest under:

```text
~/.local/share/pipetune/installed-profiles/
```

The manifest identifies the installed config path, checksum, backup path, and rollback status.

## 3. Rollback Safety
Rollback requires:

```bash
pipetune profile rollback <install_id> --confirm-rollback
```

or:

```bash
pipetune profile rollback --latest --confirm-rollback
```

Without confirmation, PipeTune refuses to modify files.

## 4. Checksum Protection
Before removing an installed config, PipeTune verifies the file checksum matches the install manifest. If the file was modified after install, rollback refuses by default.

## 5. Manual Restart
PipeTune does not restart services. After rollback, it prints:

```bash
systemctl --user restart pipewire pipewire-pulse wireplumber
```

## 6. Failure Cases
Rollback refuses when:
- the install manifest is missing
- the installed config is missing
- the installed config path is outside the user-level PipeWire config directory
- the filename is not PipeTune-owned
- the checksum does not match
- the install is already rolled back

## 7. What Rollback Will Not Remove
Rollback will not remove arbitrary files, system files, non-PipeTune user config files, or files whose checksum no longer matches the manifest.
