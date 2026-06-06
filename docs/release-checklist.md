# Release Checklist

Use this checklist before tagging a PipeTune Linux release.

## Preconditions

- Start from a clean working tree.
- Confirm no unrelated local artifacts are present.
- Confirm no compiled LV2 `.so` or `.o` artifacts are staged.
- Confirm the version and codename match the intended release.

## Warnings

- **Do not commit `.so` or `.o` files.** These are compiled plugin artifacts and must be gitignored.
- **Do not commit `dist/` or `build/`.** These are build artifacts and must be gitignored.
- **Do not commit `*.egg-info/`.** This is a development artifact and must be gitignored.
- **Do not tag with a failing release check.** If `pipetune release check` reports fail, fix the issue first.
- **Do not claim audio improvement without measurement evidence.** Profiles without source documentation are rejected.

## Cleaning Local Development Artifacts Before Release

Before running the release check, clean up gitignored local development artifacts:

```bash
pipetune package clean-local --dry-run
pipetune package clean-local
```

`clean-local` removes: `__pycache__/`, `.pytest_cache/`, `*.egg-info/`, `dist/`, `build/`, and compiled plugin artifacts (`.so`, `.o`). It does not remove source files, docs, profile database files, test files, or LV2 source files.

## Local Verification

Run in sequence. Stop if any step fails.

```bash
git status --short
python -m pytest -q
pipetune package clean-local
pipetune release check
pipetune package artifact-check
pipetune profiles validate-db
pipetune plugin build --local
pipetune plugin clean --local
git diff --check
git status --short
```

Individual steps for troubleshooting:

```bash
pipetune version
pipetune package inspect
pipetune package build-check
pipetune package smoke-test
pipetune package artifact-check
pipetune package clean-local --dry-run
pipetune plugin validate --metadata
pipetune plugin validate --rt-safety
```

## Tagging

Only tag after `pipetune release check` reports `pass` or `warn` (no `fail`).

```bash
git tag -a vX.Y.Z -m "PipeTune Linux vX.Y.Z <Codename>"
git push
git push origin vX.Y.Z
```

Example for v0.6.1:

```bash
git tag -a v0.6.1 -m "PipeTune Linux v0.6.1 Release Quality Gates and CI Foundation"
git push
git push origin v0.6.1
```

## Fresh Checkout Verification

To verify PipeTune installs from scratch correctly:

```bash
bash scripts/fresh-checkout-smoke.sh
```

## Release Notes

Release notes should include:

- Version and codename.
- User-visible commands added or changed.
- Safety boundaries confirmed.
- Known limitations.
- Whether optional LV2 validation tools were available during verification.
- Confirmation that no GUI, daemon, global LV2 install, routing automation, or DSP feature expansion was added unless explicitly in scope.

## Rollback and Safety Note

If a release needs to be withdrawn, remove or supersede the tag according to project policy. PipeTune release verification must remain non-mutating: no PipeWire, WirePlumber, ALSA, service, system config, or user audio config should be changed by package checks.
