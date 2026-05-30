"""Typed models for diagnostics, command execution, and risk findings."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class CommandResult:
    command: str
    available: bool
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool
    error: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RiskFinding:
    severity: str
    code: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"severity": self.severity, "code": self.code, "message": self.message}
