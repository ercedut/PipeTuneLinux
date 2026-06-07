# PipeTune Linux

PipeTune Linux is a safety-first Linux audio CLI for PipeWire-based systems.

## v0.9.2: CI Green and WirePlumber Install Safety Polish
v0.9.2 fixes the CI Ubuntu package dependency (`sord` does not exist on noble; `sord-validate || true` is used instead), adds `pipetune wireplumber install-preflight` (read-only environment check before install-rule), `pipetune wireplumber install-guide` (safe step-by-step workflow), CI dependency and WirePlumber safety gates in `pipetune release check`, and improved safety output for install/rollback commands. See `docs/wireplumber-rule-install-rollback.md`.

## v0.9.1: WirePlumber Rule Install State Integrity and Recovery
v0.9.1 adds `pipetune wireplumber rule-state-doctor` (read-only), `verify-rule`, `repair-rule-state --dry-run`, `cleanup-rolled-back-rules`, duplicate install protection, and checksum-mismatch rollback protection. No service is restarted. No routing is changed. See `docs/wireplumber-rule-state-integrity.md`.

## v0.9.0: User-Level WirePlumber Rule Install/Rollback Foundation
v0.9.0 adds safe, explicit user-level WirePlumber rule installation (`install-rule --user-only --confirm-install`), rollback (`rollback-rule --confirm-rollback`), and manifest-based state tracking. Install requires both `--user-only` and a mode flag. Dry-run writes nothing. No service is restarted. Rule takes effect only after user manually reloads WirePlumber. See `docs/wireplumber-rule-install-rollback.md`.

## v0.8.2: CI LV2 Validator Dependency Handling Patch
v0.8.2 fixes a CI failure where `lv2_validate` exists but `sord_validate` (its helper) is missing. The failure is now a `warn` instead of `fail`. Real TTL validation errors still fail.

## v0.8.1: WirePlumber Rule Preview and Bluetooth Policy Hardening
v0.8.1 adds `pipetune bluetooth policy-audit` for Bluetooth profile diagnostics, `pipetune wireplumber suggest-rule --user-only --dry-run` to generate a PREVIEW ONLY rule skeleton (never installed), `pipetune wireplumber validate-preview` to validate preview safety, and `pipetune route recommend` for routing improvement suggestions. All commands are read-only. Rule previews are written only to repo-local `previews/wireplumber/` paths. See [docs/bluetooth-policy-diagnostics.md](docs/bluetooth-policy-diagnostics.md) and [docs/wireplumber-rule-preview.md](docs/wireplumber-rule-preview.md).

## v0.8.0: WirePlumber and Routing Diagnostics Foundation
v0.8.0 adds read-only WirePlumber, PipeWire routing, and Bluetooth diagnostics. All commands observe and report only — no routing is changed, no services are restarted, no config is written.

## v0.7.1: Release Gate Cleanup and Profile DB Packaging Hardening
v0.7.1 adds `pipetune package clean-local` to remove safe local development artifacts, improves artifact-check to clearly distinguish removable vs. forbidden artifacts, and hardens profile DB packaging verification. After running `clean-local`, `release check` reliably returns `pass`.

## v0.7.0: Device Profile Database and Contribution Workflow Foundation
v0.7.0 adds a community-maintainable device profile database with metadata schema, quality classes, safety validation, and read-only listing/search commands. Profile commands are read-only — no profile is installed or auto-applied.

## Quick Start
```bash
git clone <repo-url>
cd PipeTuneLinux
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
pipetune version
pipetune doctor
pipetune package inspect
```

## What v0.6.1 Adds
- `pipetune package artifact-check` — detects forbidden artifacts (compiled .so/.o, dist/, build/, egg-info) and staged forbidden files.
- `pipetune release check` — runs all local release quality gates in one command with a pass/warn/fail verdict.
- `pipetune release check --json` and `pipetune package artifact-check --json` — machine-readable JSON output.
- GitHub Actions CI at `.github/workflows/ci.yml` (5 jobs: tests, packaging checks, CLI smoke, artifact hygiene, plugin validation).
- `scripts/fresh-checkout-smoke.sh` — verifies install from a clean git archive without network.
- `docs/ci.md` — CI documentation.
- `pyproject.toml` dev extras now include `build`, `setuptools`, and `wheel`.
- `pipetune package build-check` now cleans up dist/ artifacts after inspection.

## What v0.6.1 Does Not Do
- Does not use sudo.
- Does not write to `/etc`, `/lib`, `/sys`, `/proc`, or system audio configuration.
- Does not restart PipeWire, WirePlumber, ALSA, or the system automatically.
- Does not create daemons, GUI, services, or automatic profile switching.
- Does not install blocked or unknown preflight profiles.
- Does not auto-apply generated measurement corrections.
- Does not claim sound quality improvement without measurement output.
- Does not improve sound directly; it improves measurement trustworthiness before any later plugin or daemon work.
- Does not install the LV2 plugin globally.
- Does not auto-route audio through the LV2 plugin.
- Does not build an audio enhancer, spatializer, mastering suite, or bass booster.
- Does not publish packages.
- Does not add Fedora COPR automation.
- Does not add Flatpak packaging.

## Installation
```bash
python -m pip install -e .
```

See [docs/install.md](docs/install.md) for fresh-checkout installation, optional LV2 build dependencies, cleanup, and uninstall steps.

## Core Usage
```bash
pipetune version
pipetune doctor
pipetune hardware quirk-status
pipetune hardware gain-audit
pipetune verify mic-status
```

## Profile Activation Flow
```bash
pipetune profile generate examples/autoeq/sennheiser-hd650.txt --name "Sennheiser HD 650"
pipetune profile manifest generated/sennheiser-hd-650.filter-chain.conf --name "Sennheiser HD 650" --type headphone
pipetune profile preflight generated/sennheiser-hd-650.filter-chain.conf
pipetune profile dry-run-install generated/sennheiser-hd-650.filter-chain.conf --user
pipetune profile install generated/sennheiser-hd-650.filter-chain.conf --user --confirm-install
```

On hardware-quirk-sensitive machines, install also requires:
```bash
pipetune profile install generated/sennheiser-hd-650.filter-chain.conf --user --confirm-install --confirm-hardware-quirk
```

PipeTune prints the manual restart command but does not run it:
```bash
systemctl --user restart pipewire pipewire-pulse wireplumber
```

## Installed Profile Commands
```bash
pipetune profile list-installed
pipetune profile activation-status
pipetune profile state-doctor
pipetune profile verify-install <install_id>
pipetune profile repair-state --dry-run
pipetune profile cleanup-rolled-back --confirm-cleanup
pipetune profile rollback --latest --confirm-rollback
pipetune profile rollback <install_id> --confirm-rollback
```

## Measurement Commands
```bash
pipetune measure generate-sweep \
  --output measurements/sweeps/log-sweep-48k.wav \
  --duration 10 \
  --sample-rate 48000 \
  --start-hz 20 \
  --end-hz 20000 \
  --amplitude 0.5

pipetune measure analyze-sweep \
  --sweep measurements/sweeps/log-sweep-48k.wav \
  --recorded measurements/recordings/laptop-speaker-recorded.wav \
  --output measurements/reports/laptop-speaker-response.json \
  --csv-output measurements/reports/laptop-speaker-response.csv

pipetune measure inspect-wav \
  --input measurements/recordings/laptop-speaker-recorded.wav

pipetune measure import-rew \
  --input measurements/rew/export.csv \
  --output measurements/imported/rew-normalized.csv

pipetune measure validate-response \
  --input measurements/imported/rew-normalized.csv

pipetune measure compare-response \
  --before measurements/before.csv \
  --after measurements/after.csv \
  --output measurements/reports/response-comparison.json

pipetune measure generate-correction \
  --input measurements/imported/rew-normalized.csv \
  --output measurements/corrections/laptop-correction-draft.toml \
  --target flat \
  --safe
```

Measurement corrections are drafts only. PipeTune does not install them, apply them, restart services, or modify audio configuration. Response comparison reports `flatter_by_variance`; it does not claim better sound.

## LV2 Safeguard Plugin
```bash
pipetune plugin info
pipetune plugin build --local
pipetune plugin clean --local
pipetune plugin validate --offline
pipetune plugin validate --metadata
pipetune plugin validate --metadata --json
pipetune plugin validate --rt-safety
```

The plugin is a conservative local safeguard foundation: preamp/headroom, mandatory high-pass filtering, and a hard safety limiter. It is not installed globally and is not routed into PipeWire automatically. Build artifacts stay under `plugins/lv2/pipetune-safeguard.lv2/` and are gitignored.

Fedora local build dependencies:
```bash
sudo dnf install gcc make lv2-devel
```

PipeTune checks for missing `gcc`, `make`, and LV2 headers before local builds, but it never runs dependency installation automatically. If `lv2_validate` is installed, metadata validation runs it; if it is missing, PipeTune reports a warning instead of adding a mandatory external validation dependency.

The limiter is a hard safety limiter only. It exists to cap samples at a configured ceiling; it is not a mastering limiter and should not be described as improving sound quality.

## Package Verification
```bash
pipetune package inspect
pipetune package build-check
pipetune package smoke-test
pipetune package artifact-check
pipetune package artifact-check --json
pipetune package clean-local --dry-run
pipetune package clean-local
```

`package inspect` reports local package metadata and project layout. `package build-check` verifies packaging readiness, runs `python -m build`, inspects archives, and cleans up dist/ after verification. Install the `build` module if missing:

```bash
python -m pip install build
```

`package smoke-test` runs non-mutating CLI checks. `package artifact-check` detects compiled plugin artifacts, dist/build/egg-info directories, and forbidden staged files.

## Release Quality Gates
```bash
pipetune release check
pipetune release check --json
```

`release check` runs all local gates in one command: version metadata, required files, package inspect/build-check/smoke-test/artifact-check, and plugin metadata/RT-safety validation. Output is a checklist with a pass/warn/fail verdict. Run this before tagging any release.

See [docs/release-checklist.md](docs/release-checklist.md) for the full release sequence.

## Privacy and Safety
- Recording requires explicit `--confirm-recording`.
- Generated repo-local configs and manifests are ignored by default.
- User-level install state is stored under `~/.local/share/pipetune/`.
- PipeTune does not upload recordings, manifests, or hardware audits.
- Mixer and hardware audit output can reveal device details; review output before sharing publicly.

## WirePlumber and Routing Diagnostics
```bash
pipetune wireplumber audit
pipetune wireplumber audit --json
pipetune route audit
pipetune route audit --json
pipetune route explain
pipetune route explain --json
pipetune route recommend
pipetune route recommend --json
```

All commands are read-only. See [docs/wireplumber-routing-diagnostics.md](docs/wireplumber-routing-diagnostics.md).

## WirePlumber Rule Preview and Bluetooth Policy
```bash
pipetune bluetooth policy-audit
pipetune bluetooth policy-audit --json
pipetune wireplumber suggest-rule --user-only --dry-run
pipetune wireplumber suggest-rule --user-only --dry-run --output previews/wireplumber/my-rule.lua
pipetune wireplumber suggest-rule --user-only --dry-run --json
pipetune wireplumber validate-preview previews/wireplumber/my-rule.lua
pipetune wireplumber validate-preview previews/wireplumber/my-rule.lua --json
```

All commands are read-only. Rule previews are PREVIEW ONLY and never installed. See [docs/bluetooth-policy-diagnostics.md](docs/bluetooth-policy-diagnostics.md) and [docs/wireplumber-rule-preview.md](docs/wireplumber-rule-preview.md).

## WirePlumber Rule Install/Rollback (v0.9.0+)
```bash
# Step-by-step workflow guide (v0.9.2)
pipetune wireplumber install-guide
# Preflight check before install (v0.9.2, read-only)
pipetune wireplumber install-preflight
# Dry-run first (always recommended)
pipetune wireplumber install-rule previews/wireplumber/my-rule.lua --user-only --dry-run
# Confirmed install (writes to $XDG_CONFIG_HOME/wireplumber/wireplumber.conf.d/)
pipetune wireplumber install-rule previews/wireplumber/my-rule.lua --user-only --confirm-install
pipetune wireplumber rule-status
pipetune wireplumber list-rules
pipetune wireplumber rollback-rule <install_id> --dry-run
pipetune wireplumber rollback-rule <install_id> --confirm-rollback
# State integrity (v0.9.1)
pipetune wireplumber rule-state-doctor
pipetune wireplumber verify-rule <install_id>
pipetune wireplumber repair-rule-state --dry-run
pipetune wireplumber cleanup-rolled-back-rules --dry-run
pipetune wireplumber cleanup-rolled-back-rules --confirm-cleanup
```

No service is restarted. Rule takes effect only after manual WirePlumber reload. See [docs/wireplumber-rule-install-rollback.md](docs/wireplumber-rule-install-rollback.md).

## Device Profile Database
```bash
pipetune profiles list
pipetune profiles list --type headphone
pipetune profiles list --quality B
pipetune profiles show <profile_id>
pipetune profiles search laptop
pipetune profiles validate-db
pipetune profiles validate-db --json
```

Profile commands are read-only. No profile is installed, applied, or routed automatically. See [docs/profile-database.md](docs/profile-database.md) and [docs/profile-contribution-guide.md](docs/profile-contribution-guide.md).

## Roadmap
- Current: v0.9.2 CI Green and WirePlumber Install Safety Polish.
- Next: v1.0 Stable Profile Generation.

See [docs/roadmap.md](docs/roadmap.md).

## License
MIT. See [LICENSE](LICENSE).
