"""Profile metadata schema constants for PipeTune Linux."""

from __future__ import annotations

VALID_PROFILE_TYPES = frozenset({
    "headphone",
    "laptop-speaker",
    "microphone",
    "bluetooth-device",
    "measurement-correction",
})

VALID_QUALITY_CLASSES = frozenset({"A", "B", "C", "D"})

VALID_SAFETY_STATUSES = frozenset({"safe", "draft", "experimental", "rejected"})

REQUIRED_METADATA_FIELDS = (
    "profile_id",
    "profile_name",
    "profile_type",
    "version",
    "device_vendor",
    "device_model",
    "device_category",
    "source_type",
    "license",
    "quality_class",
    "safety_status",
    "maintainer",
    "notes",
)

QUALITY_CLASS_DESCRIPTIONS = {
    "A": "Measured with documented equipment and reproducible method",
    "B": "Derived from trusted open database (e.g., AutoEQ)",
    "C": "Conservative generic safe profile",
    "D": "Experimental / not installed by default",
}

SAFETY_STATUS_DESCRIPTIONS = {
    "safe": "Reviewed and approved for general use",
    "draft": "Work in progress — not approved for general use",
    "experimental": "Experimental — use with caution",
    "rejected": "Rejected — must not be exported or applied",
}

PROFILES_SUBDIR_TO_TYPE = {
    "headphones": "headphone",
    "speakers": "laptop-speaker",
    "microphones": "microphone",
    "bluetooth": "bluetooth-device",
}
