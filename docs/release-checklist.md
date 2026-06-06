# Release Checklist

Use this checklist before tagging a PipeTune Linux release.

## Preconditions

- Start from a clean working tree.
- Confirm no unrelated local artifacts are present.
- Confirm no compiled LV2 `.so` or `.o` artifacts are staged.
- Confirm the version and codename match the intended release.

## Local Verification

```bash
python -m pytest -q
pipetune version
pipetune package inspect
pipetune package build-check
pipetune package smoke-test
pipetune plugin info
pipetune plugin validate --metadata
pipetune plugin validate --rt-safety
pipetune plugin build --local
pipetune plugin clean --local
git status --short
git check-ignore -v plugins/lv2/pipetune-safeguard.lv2/pipetune_safeguard.so || true
git check-ignore -v plugins/lv2/pipetune-safeguard.lv2/pipetune_safeguard.o || true
```

If `pipetune package build-check` reports that the optional Python build module is missing, install it manually:

```bash
python -m pip install build
```

Do not publish packages from `build-check`; it is local-only.

## Tagging

Tag format:

```text
vX.Y.Z
```

Example:

```bash
git tag -a v0.6.0 -m "PipeTune Linux v0.6.0"
git push origin main
git push origin v0.6.0
```

## Release Notes

Release notes should include:

- Version and codename.
- User-visible commands added or changed.
- Safety boundaries.
- Known limitations.
- Whether optional LV2 validation tools were available during verification.
- Confirmation that no GUI, daemon, global LV2 install, routing automation, or DSP feature expansion was added unless that is explicitly the release scope.

## Rollback And Safety Note

If a release needs to be withdrawn, remove or supersede the tag according to project policy and publish a correction note. PipeTune release verification must remain non-mutating: no PipeWire, WirePlumber, ALSA, service, system config, or user audio config should be changed by package checks.
