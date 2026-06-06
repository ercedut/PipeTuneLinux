# Profile Submission Template

Use this template when submitting a new TOML profile file to the PipeTune Linux profile database.

## Profile File

Attach or paste the TOML profile file below. All required `[metadata]` fields must be present.

Required fields:
- `profile_id` — unique, kebab-case identifier
- `profile_name` — human-readable display name
- `profile_type` — headphone / laptop-speaker / microphone / bluetooth-device / measurement-correction
- `version` — semantic version (e.g., 0.1.0)
- `device_vendor` — manufacturer or "generic"
- `device_model` — model name or "generic"
- `device_category` — subcategory (e.g., over-ear, laptop, built-in)
- `source_type` — autoeq-database / measured / generic-conservative / policy-note / other
- `source_url` or `source_reference` — at least one must be present
- `license` — compatible open license
- `quality_class` — A / B / C / D
- `safety_status` — safe / draft / experimental / rejected
- `created_at` — ISO date (YYYY-MM-DD)
- `maintainer` — GitHub username or contact
- `notes` — any important caveats

For `laptop-speaker` type, a `[safeguards]` section is required:

```toml
[safeguards]
hpf_hz = 120
limiter_ceiling_db = -1.0
```

## Verification Checklist

- [ ] `pipetune profiles validate-db` passes with this profile added.
- [ ] Profile ID is unique and does not duplicate an existing profile.
- [ ] Source URL or reference is accessible and accurately describes the data.
- [ ] License is confirmed and compatible.
- [ ] For quality class A: measurement method and equipment are documented.
- [ ] For laptop-speaker: HPF and limiter safeguards are present.
- [ ] `safety_status` is `draft` unless this is a verified, reviewed profile.
- [ ] EXAMPLE profiles are clearly labeled in `notes`.
- [ ] No bass boost below the HPF frequency is present without documented justification.

## Why This Profile Should Be Included

Explain why this profile is:
- Based on credible source data
- Safe to include (even as a draft)
- Useful to the community
- Not a duplicate of an existing profile

## Confirmation

- [ ] I have permission to submit this data under the stated license.
- [ ] I understand this submission will be reviewed by a maintainer before merging.
- [ ] I confirm this profile does not auto-apply audio changes when added to the database.
