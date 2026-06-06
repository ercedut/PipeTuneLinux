# Device Profile Database

PipeTune Linux maintains a community-maintainable profile database for headphones, laptop speakers, microphones, and Bluetooth audio devices.

## Profile Quality Classes

Every profile has a quality class that describes the confidence level of its source data.

| Class | Description |
|---|---|
| A | Measured with documented equipment and reproducible method |
| B | Derived from trusted open database (e.g., AutoEQ) |
| C | Conservative generic safe profile |
| D | Experimental / not installed by default |

Class A requires documented measurement equipment, method, and reproducibility. Class B requires a referenced database entry with a verifiable URL. Class C is for profiles that apply only conservative, well-understood transforms (e.g., high-pass filtering within known safe limits). Class D is for experimental profiles that have not been validated for general use.

## Profile Safety Statuses

| Status | Description |
|---|---|
| `safe` | Reviewed and approved for general use |
| `draft` | Work in progress — not approved for general use |
| `experimental` | Use with caution |
| `rejected` | Must not be exported or applied |

`rejected` profiles remain in the database for audit purposes but are blocked from any export or apply operation.

## Why Unsourced Profiles Are Rejected

All profiles must have either a `source_url` or a `source_reference`. Profiles without a verifiable source cannot be reviewed for accuracy or safety. An unsourced EQ profile could introduce:

- Excessive bass boost that stresses speaker drivers.
- High-frequency boosts that cause ear fatigue or damage.
- Frequency response curves that do not match the target device.

## Why Laptop Speaker Profiles Require HPF and Limiter

Laptop speakers have strict power and physical limits. Without a high-pass filter (HPF), low-frequency energy can damage speaker drivers. Without a hard limiter, software gain can exceed safe playback levels.

All `laptop-speaker` profiles must include a `[safeguards]` section:

```toml
[safeguards]
hpf_hz = 120
limiter_ceiling_db = -1.0
```

`hpf_hz` must reflect a safe HPF cut-off for the target device class. `limiter_ceiling_db` must be negative (below 0 dBFS). Bass boost below the HPF frequency is rejected without documented justification.

## Why Measurement-Correction Profiles Stay Draft Until Reviewed

Measurement-correction profiles are generated from local hardware measurements, which vary by recording setup, microphone quality, and room conditions. Even accurate measurements can produce correction profiles that are safe for one device but harmful to another. These profiles stay `draft` until a maintainer has reviewed the source data and measurement method.

## Listing and Inspecting Profiles

```bash
pipetune profiles list
pipetune profiles list --type headphone
pipetune profiles list --quality B
pipetune profiles show <profile_id>
pipetune profiles search laptop
pipetune profiles search autoeq
```

None of these commands install or apply profiles.

## Validating the Profile Database

```bash
pipetune profiles validate-db
pipetune profiles validate-db --json
```

This command reads and validates all profile files. It checks required fields, unique IDs, known types and quality classes, source and license presence, laptop-speaker safeguards, and measurement-correction status. It does not install, apply, or modify any audio configuration.

## Licensing

All profiles must carry an open license that is compatible with the project license (MIT). The source data must be attributed and its license confirmed at submission time.
