"""
Shared configuration constants for AutoFX.

This module is intentionally dependency-free so it can be imported cheaply
from anywhere (e.g. CLI argument parsing) without pulling in heavy rendering
or SDK dependencies.
"""

# Default Claude model used for shader generation.
# This is the single source of truth — update it here only.
DEFAULT_MODEL = "claude-opus-4-8"
