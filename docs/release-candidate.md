# PipeTune Linux v1.0.0-rc1 Release Candidate

## What v1.0.0-rc1 Means

v1.0.0-rc1 is the first release candidate for PipeTune Linux v1.0.0 Stable. It represents a safety-frozen, audited, and hardened codebase. The tool is usable for diagnostics, measurement, profile generation, safe WirePlumber rule management, and release validation on Fedora KDE and compatible Linux audio systems.

A release candidate means:
- All known correctness bugs in scope are fixed.
- No new features will be added before v1.0.0 Stable.
- Safety boundaries are enforced and frozen.
- CI passes. Release check passes. All RC gates pass.
- Real Fedora KDE manual smoke testing is documented and expected.

## What Is Frozen in v1.0.0-rc1

The following are frozen and will not change before v1.0.0 Stable unless a critical correctness bug is found:

- CLI command interface and argument names.
- JSON output schemas for all commands.
- Safety boundaries (no system mutation, no service restart, no global LV2 install, no automatic routing).
- Profile database schema.
- WirePlumber rule install/rollback workflow (XDG isolation, manifest tracking, dry-run requirement).
- LV2 plugin safeguard architecture.

## What Is Not Frozen

- Documentation improvements.
- Test coverage expansions.
- Cosmetic CLI output improvements.
- New diagnostic commands that do not mutate system state.

## Known Limitations

- `repair-state` is dry-run only; actual state repair is proposed but not applied.
- Live PipeWire/WirePlumber service queries return empty if those services are not running.
- Bluetooth hardware presence is optional; commands gracefully degrade when no Bluetooth device is present.
- The LV2 plugin is a local safeguard only; it is not installed globally and is not routed into PipeWire automatically.
- Measurement commands produce approximate results and are not calibrated.
- `sord-validate` is optional for LV2 validation; its absence produces a warning, not a failure.

## Required Local Checks Before Tagging v1.0.0 Stable

Run these commands in sequence. Stop if any fails.

```bash
git config user.name "Erce Dutkan"
git config user.email "erceyem@gmail.com"
git status --short
python -m pytest -q
pipetune package clean-local
pipetune rc mutation-audit
pipetune rc docs-check
pipetune rc command-matrix
pipetune rc audit
pipetune release check
pipetune package artifact-check
git diff --check
git status --short
```

## Required CI Checks

All CI jobs must pass:
- `test` (Python 3.11 and 3.12)
- `packaging-check`
- `cli-smoke-check`
- `artifact-hygiene`
- `plugin-validation`
- `rc-gates`

## Fedora KDE Smoke Procedure

Run the full non-mutating smoke suite on a real Fedora KDE system:

```bash
pipetune rc fedora-smoke
pipetune rc fedora-smoke --json
```

Expected result: `Verdict: pass` or `Verdict: warn` (warn is acceptable for absent Bluetooth hardware or unavailable live audio services). `Verdict: fail` blocks release.

Alternatively, run individual commands manually:

```bash
pipetune version
pipetune doctor
pipetune package inspect
pipetune package artifact-check
pipetune plugin validate --metadata
pipetune plugin validate --rt-safety
pipetune profiles validate-db
pipetune wireplumber audit
pipetune route audit
pipetune bluetooth policy-audit
pipetune wireplumber install-preflight
pipetune wireplumber rule-state-doctor
pipetune release check
pipetune rc audit
```

## How to Report Issues

Open an issue in the project repository with:
- PipeTune version (`pipetune version`)
- Linux distribution and desktop environment
- Command run and full output
- Expected vs. actual behavior

## How to Rollback WirePlumber Rules

If a WirePlumber rule was installed with `install-rule --confirm-install`:

```bash
pipetune wireplumber rule-status
pipetune wireplumber rollback-rule <install_id> --dry-run
pipetune wireplumber rollback-rule <install_id> --confirm-rollback
```

After rollback, manually reload WirePlumber to apply changes:

```bash
systemctl --user restart wireplumber
```

PipeTune does not restart WirePlumber automatically.

## Safety Boundaries

PipeTune v1.0.0-rc1 does **not**:

- Install packages, system libraries, or audio drivers.
- Write to `/etc`, `/usr`, `/lib`, or `/sys`.
- Restart PipeWire, WirePlumber, or any system service.
- Change default audio routing or sink/source assignment.
- Switch Bluetooth profiles.
- Install the LV2 plugin globally.
- Route audio through the LV2 plugin automatically.
- Require root or `sudo` for normal operation.
- Upload diagnostics, recordings, or hardware audits to external services.

The only file writes in production code are:
- User-specified output files (WAV, JSON, CSV, TOML) for measurement commands.
- User-level WirePlumber config (`$XDG_CONFIG_HOME/wireplumber/wireplumber.conf.d/`) when `install-rule --confirm-install` is explicitly confirmed.
- Repo-local preview files (`previews/wireplumber/`) when `suggest-rule --dry-run --user-only` is used.
- Repo-local hardware quirk report bundles (`quirk-report`).

## No Automatic Audio Routing

PipeTune does not change default audio sinks, sources, or routing. Route diagnostics are read-only. The `route recommend` command prints recommendations but does not apply them.

## No Daemon

PipeTune has no background process, daemon, service, or auto-update mechanism.

## No GUI

PipeTune is a CLI tool. GUI is planned for v2.0 and is out of scope for v1.0.0 and v1.0.0-rc1.

## No Claims of Audio Improvement Without Measurement

Profiles are never automatically applied. Measurement commands produce reports, not conclusions. `compare-response` reports `flatter_by_variance` — a variance metric — not "better sound".

## What v1.0.0-rc1 Gives Users

- A complete, auditable, safety-first Linux audio diagnostics and profile management CLI.
- Safe WirePlumber rule installation with dry-run, confirmation, manifest tracking, and rollback.
- Measurement workflows (sweep generation, response analysis, REW import, correction drafts).
- A device profile database with validation and contribution workflows.
- Release-candidate quality gates (`rc audit`, `rc mutation-audit`, `rc docs-check`, `rc fedora-smoke`).
- Full CI coverage with safety gates on every push.

## Next: v1.0.0 Stable

v1.0.0 Stable will follow after successful real-system manual smoke testing on Fedora KDE, CI green, and resolution of any issues found during the rc1 phase. The safety freeze established in v1.0.0-rc1 will be maintained.
