# Profile Contribution Guide

This guide explains how to contribute profiles to the PipeTune Linux device profile database.

## Before You Contribute

Read [docs/profile-database.md](profile-database.md) first to understand:

- Quality classes and what evidence is required for each.
- Why laptop-speaker profiles require HPF and limiter safeguards.
- Why unsourced profiles are rejected.
- Licensing requirements.

## Profile Types

| Type | Description |
|---|---|
| `headphone` | Over-ear, on-ear, or in-ear headphones |
| `laptop-speaker` | Built-in laptop or portable speaker |
| `microphone` | Built-in or external microphone |
| `bluetooth-device` | Bluetooth audio device |
| `measurement-correction` | Correction derived from local measurement |

## Submitting a Profile Request

If you want a profile added but cannot create the TOML file yourself, use the request template at `profiles/templates/profile-request.md`. Fill in the device details, source information, and safety notes, and open an issue.

## Submitting a Profile File

1. Create a TOML file using the submission template at `profiles/templates/profile-submission.md`.
2. Place the file in the appropriate subdirectory:
   - `profiles/headphones/` for headphones
   - `profiles/speakers/` for laptop speakers
   - `profiles/microphones/` for microphones
   - `profiles/bluetooth/` for Bluetooth devices
3. Run `pipetune profiles validate-db` to verify the file passes all checks.
4. Open a pull request with the new profile file only. Do not include unrelated changes.

## Required Metadata Fields

Every profile must have all of these fields in the `[metadata]` section:

```toml
[metadata]
profile_id = "vendor-model-type-version"
profile_name = "Human-readable name (Source)"
profile_type = "headphone"
version = "0.1.0"
device_vendor = "Sennheiser"
device_model = "HD 650"
device_category = "over-ear"
source_type = "autoeq-database"
source_url = "https://..."
license = "MIT"
quality_class = "B"
safety_status = "draft"
created_at = "2026-06-06"
maintainer = "your-github-username"
notes = "Brief notes on the profile and any caveats."
```

Use `source_url` for a direct link or `source_reference` for a bibliographic reference. At least one must be present.

## Laptop Speaker Safeguard Requirements

All `laptop-speaker` profiles must include:

```toml
[safeguards]
hpf_hz = 120
limiter_ceiling_db = -1.0
```

- `hpf_hz`: The high-pass filter cutoff frequency. Must be chosen to protect the speaker drivers. 80–150 Hz is typical for laptops; justify lower values with measurement data.
- `limiter_ceiling_db`: The hard limiter ceiling. Must be negative. `-1.0` is a safe default.

Profiles without these fields will be rejected by `pipetune profiles validate-db`.

## How Maintainers Review Profiles

Maintainers check:

1. All required metadata fields are present and valid.
2. The source URL or reference is accessible and accurately describes the data.
3. The license is confirmed and compatible.
4. For quality class A: measurement method and equipment are documented.
5. For `laptop-speaker`: HPF and limiter safeguards are present and reasonable.
6. For `measurement-correction`: safety status is `draft`.
7. No duplicate `profile_id` or duplicate device/type combination (unless versioned differently).

Profiles that pass review may have their `safety_status` changed from `draft` to `safe` by a maintainer.

## CI Validation

Every pull request runs `pipetune profiles validate-db` in CI. The CI workflow will fail if any profile fails validation. Check the CI output before requesting review.

## What Gets Rejected

- Profiles without a verifiable source.
- Profiles without a license.
- Laptop-speaker profiles without HPF and limiter safeguards.
- Profiles with duplicate `profile_id`.
- Profiles with unknown `quality_class` or `safety_status`.
- Profiles claiming quality class A without documented measurement equipment and method.
- Bass boost below the HPF frequency without documented justification.

## Safety Principle

PipeTune does not auto-apply profiles. Adding a profile to the database does not install it or change any audio configuration. The database is a reference resource only.
