# WirePlumber Rule Install and Rollback

PipeTune Linux can install and rollback user-level WirePlumber rules in a safe, reversible, and auditable way.

## Safety guarantees

- **User-level only.** Rules are installed under `XDG_CONFIG_HOME/wireplumber/wireplumber.conf.d/` (defaults to `~/.config/wireplumber/wireplumber.conf.d/`). No system paths (`/etc`, `/usr`, `/lib`, `/sys`) are ever written.
- **No service restart.** PipeTune does not restart WirePlumber, PipeWire, pipewire-pulse, or any audio service. Users must manually reload/restart WirePlumber outside PipeTune if they want a rule to take effect.
- **No routing change.** PipeTune does not call `wpctl set-default`, `pactl set-default-sink`, `pactl set-card-profile`, or any routing command.
- **Dry-run first.** All write operations require either `--dry-run` or a confirmed flag. Always run dry-run first.
- **Manifest tracking.** Every install creates an `install_id` and records the checksum, path, and timestamp in a local manifest (`PIPETUNE_HOME/wireplumber-rules/manifests.json`).
- **Checksum mismatch protection.** Rollback refuses to delete an installed file if its content does not match the manifest checksum. This prevents accidental deletion of manually-modified files.
- **Duplicate install protection.** `install-rule` refuses if a rule with the same checksum is already active.

## Recommended workflow

Follow the `install-guide` output for the complete safe workflow:

```bash
pipetune wireplumber install-guide
```

Short form:

1. Generate a preview: `pipetune wireplumber suggest-rule --dry-run --user-only`
2. Validate: `pipetune wireplumber validate-preview <preview_file>`
3. Preflight: `pipetune wireplumber install-preflight`
4. Dry-run install: `pipetune wireplumber install-rule <preview_file> --user-only --dry-run`
5. Confirm install: `pipetune wireplumber install-rule <preview_file> --user-only --confirm-install`
6. Review the installed file manually.
7. If desired, reload WirePlumber manually outside PipeTune.
8. Rollback if needed: `pipetune wireplumber rollback-rule <install_id> --dry-run` then `--confirm-rollback`

## install-preflight

Read-only preflight check that verifies the environment before installation.

```bash
pipetune wireplumber install-preflight
pipetune wireplumber install-preflight --json
```

Checks:
- WirePlumber and PipeWire service status
- User-level config directory existence and writability
- Manifest file accessibility
- Existing PipeTune rule state (via `rule-state-doctor`)
- Whether test isolation env vars (`XDG_CONFIG_HOME`, `PIPETUNE_HOME`) are active

This command is **read-only**: it creates no files, restarts no services, and changes no routing.

## install-rule

```bash
pipetune wireplumber install-rule <preview_file> --user-only --dry-run
pipetune wireplumber install-rule <preview_file> --user-only --confirm-install
pipetune wireplumber install-rule <preview_file> --user-only --confirm-install --json
```

- `--user-only` is always required.
- `--dry-run` shows what would be installed without writing anything.
- `--confirm-install` performs the actual install.
- Dry-run output includes the exact confirmed install command.
- Confirmed install output includes the rollback command.

## rollback-rule

```bash
pipetune wireplumber rollback-rule <install_id> --dry-run
pipetune wireplumber rollback-rule <install_id> --confirm-rollback
```

- Dry-run shows what would be removed without changing anything.
- Confirmed rollback removes the installed file and marks the manifest entry as `rolled_back`.
- If checksum does not match, rollback is refused.
- After rollback, WirePlumber must be manually reloaded outside PipeTune for the change to take effect.

## Test isolation

All tests use isolated `XDG_CONFIG_HOME` and `PIPETUNE_HOME` via `tmp_path` fixtures. No real `~/.config/wireplumber` is ever written during testing.

## Ubuntu CI package note

The Ubuntu package `sord` does not exist on Ubuntu 24.04 (noble). CI uses `lv2-dev` and `lilv-utils` as required packages, and `sord-validate || true` as an optional package. See `docs/ci.md` for details.
