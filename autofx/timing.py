"""
Timing instrumentation for AutoFX pipeline.

Collects timing data from each stage and prints a summary.
"""

import time
from contextlib import contextmanager
from typing import List, Optional


class Timer:
    """Collects timing events and prints a summary."""

    def __init__(self):
        self.events: List[dict] = []
        self._start_time: Optional[float] = None

    def start(self):
        """Mark the overall start time."""
        self._start_time = time.monotonic()

    @contextmanager
    def phase(self, name: str):
        """Time a named phase of the pipeline."""
        t0 = time.monotonic()
        yield
        elapsed = time.monotonic() - t0
        self.events.append({"name": name, "elapsed": elapsed})

    def record(self, name: str, elapsed: float):
        """Record a timing event directly."""
        self.events.append({"name": name, "elapsed": elapsed})

    def summary(self) -> str:
        """Return a formatted timing summary."""
        if not self.events:
            return "No timing data recorded."

        total = time.monotonic() - self._start_time if self._start_time else sum(e["elapsed"] for e in self.events)

        lines = ["\n--- Timing Breakdown ---"]

        for event in self.events:
            elapsed = event["elapsed"]
            pct = (elapsed / total * 100) if total > 0 else 0
            lines.append(f"  {event['name']:<40s} {elapsed:7.2f}s  ({pct:4.1f}%)")

        lines.append(f"  {'─' * 55}")
        lines.append(f"  {'Total':<40s} {total:7.2f}s")
        lines.append("")

        return "\n".join(lines)


# Global timer instance
_timer = Timer()


def get_timer() -> Timer:
    """Get the global timer instance."""
    return _timer


def reset_timer():
    """Reset the global timer."""
    global _timer
    _timer = Timer()
