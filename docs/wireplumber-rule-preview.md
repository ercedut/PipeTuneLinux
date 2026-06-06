# WirePlumber Rule Preview

PipeTune v0.8.1 adds the ability to generate a **preview-only** WirePlumber rule skeleton. The rule is never installed. It is written to a repo-local `previews/wireplumber/` path for manual review only.

## Commands

### pipetune wireplumber suggest-rule

Generates a rule preview skeleton. Both `--dry-run` and `--user-only` are required.

```bash
pipetune wireplumber suggest-rule --user-only --dry-run
pipetune wireplumber suggest-rule --user-only --dry-run --json
pipetune wireplumber suggest-rule --user-only --dry-run --output previews/wireplumber/example-rule.lua
```

- Without `--dry-run`: refused.
- Without `--user-only`: refused.
- Without both: refused.
- With `--output`: must be a repo-local path under `previews/wireplumber/` or `reports/wireplumber/`.
- Paths under `~/.config/wireplumber/`, `/etc/`, `/lib/`, `/usr/`, `/sys/`, or any system path: refused.
- Paths outside the repository root: refused.

The generated preview contains:
- A strong `PREVIEW ONLY — NOT INSTALLED` header.
- The reason for suggestion.
- A skeleton rule structure (not a production rule).
- A rollback note (delete the file if manually applied).
- Source diagnostic summary.
- Limitations.

### pipetune wireplumber validate-preview \<path\>

Validates a preview file to confirm it is safe and properly annotated.

```bash
pipetune wireplumber validate-preview previews/wireplumber/example-rule.lua
pipetune wireplumber validate-preview previews/wireplumber/example-rule.lua --json
```

Validation checks:
- File exists.
- Contains `PREVIEW ONLY` marker.
- Contains `NOT INSTALLED` marker.
- No dangerous Lua patterns detected (e.g., `os.execute`, `io.open`, `require`).
- Path is a repo-local allowed preview path.
- Path does not target `/etc/` or `~/.config/` directly.

## Why Rules Are Not Installed in v0.8.1

Installing a WirePlumber rule requires:
1. Knowing the exact device name and policy target.
2. Understanding the WirePlumber Lua API.
3. Testing that the rule does not break other devices or services.
4. A rollback mechanism if the rule causes problems.

PipeTune v0.8.1 provides only a preview skeleton. The rule content is a placeholder for manual review. Future versions may add validated rule generation with explicit install and rollback commands.

## Allowed Preview Output Paths

Preview files may only be written to:
- `previews/wireplumber/` (relative to repo root)
- `reports/wireplumber/` (relative to repo root)

Refused paths:
- `~/.config/wireplumber/` — this would install the rule
- `/etc/wireplumber/` — system-wide install
- Any path outside the repository root

## Safety

- `suggest-rule` never writes to system paths.
- `validate-preview` never modifies files.
- No WirePlumber service is restarted.
- No routing is changed.
- All JSON outputs include `safety.rule_installed: false` and `safety.changed_routing: false`.
