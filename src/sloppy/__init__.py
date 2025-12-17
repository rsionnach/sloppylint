"""Sloppy - Python AI Slop Detector."""

try:
    from importlib.metadata import version

    __version__ = version("sloppylint")
except Exception:
    __version__ = "0.0.0"  # Fallback for development
