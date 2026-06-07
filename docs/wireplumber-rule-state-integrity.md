# WirePlumber Rule Install State Integrity

PipeTune Linux v0.9.1 introduced read-only integrity checks for installed WirePlumber rules.

## Commands

### rule-state-doctor

Read-only integrity check for all installed rules.

```bash
pipetune wireplumber rule-state-doctor
pipetune wireplumber rule-state-doctor --json
```

Reports:
- Missing installed files for active rules
- Checksum mismatches (file modified after install)
- Orphan PipeTune-prefixed files not in the manifest
- Duplicate active `rule_id`s

### verify-rule

Read-only verification of a single installed rule.

```bash
pipetune wireplumber verify-rule <install_id>
```

### repair-rule-state

Dry-run only: proposes repair actions without modifying any files.

```bash
pipetune wireplumber repair-rule-state --dry-run
```

### cleanup-rolled-back-rules

Removes manifest entries where status is `rolled_back` and the installed file is absent.

```bash
pipetune wireplumber cleanup-rolled-back-rules --dry-run
pipetune wireplumber cleanup-rolled-back-rules --confirm-cleanup
```

## Integrity model

Each installed rule has:
- `install_id`: unique 8-character hex identifier
- `rule_id`: `pipetune-rule-<install_id>`
- `installed_path`: absolute path under user config dir
- `checksum`: `sha256:<hex>` of the rule file content at install time
- `status`: `active` or `rolled_back`
- `created_at`, `rolled_back_at`: ISO timestamps

### Invariants enforced

- Active rules must have their installed file present and checksum must match.
- Rollback refuses if the file's current checksum does not match the manifest (prevents deleting a manually-modified file).
- Install refuses if a rule with the same checksum is already active (duplicate install protection).

## Safety

All state doctor, verify-rule, and repair-rule-state commands are **read-only**. No service is restarted, no routing is changed, and no system configuration is modified. Only `cleanup-rolled-back-rules --confirm-cleanup` modifies the manifest (removes safe entries only).

## Test isolation

All tests use isolated `PIPETUNE_HOME` via `tmp_path` fixtures. No real `~/.local/share/pipetune` is written during testing.
