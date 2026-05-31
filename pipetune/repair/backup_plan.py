"""Manual-only backup planning for HDA retask files."""

from __future__ import annotations

from pathlib import Path

from pipetune.repair.hda_plan import DEFAULT_AUDIT_DIR


def _discover_retask_paths(audit_dir: Path) -> list[str]:
    paths = {
        "/etc/modprobe.d/hda-jack-retask.conf",
        "/lib/firmware/hda-jack-retask.fw",
    }

    search_file = audit_dir / "raw" / "hda-retask-search.txt"
    if search_file.exists():
        try:
            text = search_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""

        for line in text.splitlines():
            if not line.startswith("/"):
                continue
            parts = line.split(":", 2)
            discovered = parts[0].strip()
            line_content = parts[2].strip().lower() if len(parts) > 2 else ""
            discovered_lower = discovered.lower()

            is_retask_candidate = any(
                token in discovered_lower for token in ("hda", "snd_hda", "retask")
            ) or any(
                token in line_content for token in ("snd-hda", "snd_hda", "hda-jack-retask", "model=")
            )

            if (
                is_retask_candidate
                and (discovered.startswith("/etc/modprobe.d") or discovered.startswith("/lib/firmware"))
            ):
                paths.add(discovered)

    return sorted(paths)


def render_backup_plan(audit_dir: Path = DEFAULT_AUDIT_DIR) -> str:
    discovered_paths = _discover_retask_paths(audit_dir)

    lines = [
        "PipeTune HDA Backup Plan",
        "",
        "MANUAL / DO NOT RUN BLINDLY",
        "These commands are printed for human review only.",
        "PipeTune does not run them automatically.",
        "",
        "Suggested manual backup sequence:",
        "1. Create a timestamped backup directory.",
        "2. Copy each discovered retask-related file if present.",
        "3. Record checksums and notes.",
        "",
        "Example manual commands:",
        "MANUAL / DO NOT RUN BLINDLY:",
        "  TS=$(date +%Y%m%d-%H%M%S)",
        "  BACKUP_DIR=~/pipetune-hda-backups/$TS",
        "  mkdir -p \"$BACKUP_DIR\"",
        "",
        "Discovered candidate files:",
    ]

    for path in discovered_paths:
        lines.append(f"- {path}")

    lines.extend(
        [
            "",
            "MANUAL / DO NOT RUN BLINDLY:",
        ]
    )

    for path in discovered_paths:
        file_name = Path(path).name
        lines.append(f"  [ -f \"{path}\" ] && cp -a \"{path}\" \"$BACKUP_DIR/{file_name}\"")

    lines.extend(
        [
            "",
            "MANUAL / DO NOT RUN BLINDLY:",
            "  (cd \"$BACKUP_DIR\" && sha256sum * > SHA256SUMS.txt 2>/dev/null || true)",
            "",
            "No system configuration was modified.",
        ]
    )

    return "\n".join(lines)
