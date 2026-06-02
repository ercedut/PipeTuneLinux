"""Measurement and calibration helpers for PipeTune Linux."""

from __future__ import annotations


class MeasurementError(ValueError):
    """Raised when measurement input is invalid or unsafe."""

