# HDA Repair Guide (Manual-Only)

## Purpose
This guide explains how to use PipeTune v0.2.2 repair planning commands for HDA routing quirks without automatically changing system state.

## Scope
- Read-only diagnostics and planning
- Manual backup-first workflow
- Explicit rollback and stop conditions

## Commands
```bash
pipetune repair hda-plan
pipetune repair backup-plan
pipetune repair checklist
```

## Safety Model
- PipeTune does not apply HDA pin changes.
- PipeTune does not edit `/etc/modprobe.d` or `/lib/firmware`.
- PipeTune does not restart audio services.

## Recommended Flow
1. Run `pipetune hardware hda-audit`.
2. Run `pipetune repair backup-plan` and prepare manual backups.
3. Run `pipetune repair hda-plan` and follow the guided sequence.
4. Use `pipetune repair checklist` during manual verification.

## Privacy
- Raw audit captures are local and gitignored under `docs/system-audits/.../raw/`.
- Public markdown summaries are sanitized.
- PipeTune does not upload audit data.
