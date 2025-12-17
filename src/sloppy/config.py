"""Configuration file support for Sloppy."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None  # type: ignore[assignment,unused-ignore]


@dataclass
class Config:
    """Sloppy configuration."""

    # Patterns to ignore (glob patterns)
    ignore: list[str] = field(default_factory=list)

    # Patterns to include (glob patterns) - only scan matching files
    include: list[str] = field(default_factory=list)

    # Pattern IDs to disable
    disable: list[str] = field(default_factory=list)

    # Minimum severity level
    severity: str = "low"

    # Maximum allowed slop score
    max_score: int | None = None

    # Output format
    format: str = "detailed"

    # CI mode
    ci: bool = False

    # Strict import checking - when True, validates imports against installed packages
    # When False (default), only checks for known AI hallucination patterns
    strict_imports: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        """Create config from a dictionary."""
        return cls(
            ignore=data.get("ignore", []),
            include=data.get("include", []),
            disable=data.get("disable", []),
            severity=data.get("severity", "low"),
            max_score=data.get("max-score"),
            format=data.get("format", "detailed"),
            ci=data.get("ci", False),
            strict_imports=data.get("strict-imports", False),
        )

    def merge_cli_args(self, args: Any) -> None:
        """Merge CLI arguments into config (CLI takes precedence)."""
        # Append CLI ignores to config ignores
        if hasattr(args, "ignore") and args.ignore:
            self.ignore.extend(args.ignore)

        # Append CLI includes to config includes
        if hasattr(args, "include") and args.include:
            self.include.extend(args.include)

        # Append CLI disables to config disables
        if hasattr(args, "disable") and args.disable:
            self.disable.extend(args.disable)

        # CLI severity overrides config (only if explicitly set)
        if hasattr(args, "severity") and args.severity != "low":
            self.severity = args.severity

        # Handle strict/lenient flags
        if hasattr(args, "strict") and args.strict:
            self.severity = "low"
        elif hasattr(args, "lenient") and args.lenient:
            self.severity = "high"

        # CLI max_score overrides config
        if hasattr(args, "max_score") and args.max_score is not None:
            self.max_score = args.max_score

        # CLI format overrides config
        if hasattr(args, "format") and args.format != "detailed":
            self.format = args.format

        # CLI ci flag takes precedence
        if hasattr(args, "ci") and args.ci:
            self.ci = True

        # CLI strict_imports flag takes precedence
        if hasattr(args, "strict_imports") and args.strict_imports:
            self.strict_imports = True


def find_config_file(start_path: Path | None = None) -> Path | None:
    """Find pyproject.toml by searching up from start_path."""
    if start_path is None:
        start_path = Path.cwd()

    current = start_path.resolve()

    # Search up the directory tree
    for parent in [current] + list(current.parents):
        pyproject = parent / "pyproject.toml"
        if pyproject.is_file():
            return pyproject

    return None


def load_config(config_path: Path | None = None) -> Config:
    """Load configuration from pyproject.toml.

    Args:
        config_path: Path to pyproject.toml, or None to search for it.

    Returns:
        Config object with loaded settings.
    """
    if tomllib is None:
        # No TOML support available
        return Config()

    # Find config file if not specified
    if config_path is None:
        config_path = find_config_file()

    if config_path is None or not config_path.is_file():
        return Config()

    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    except Exception:
        return Config()

    # Look for [tool.sloppy] section
    tool_config = data.get("tool", {}).get("sloppy", {})

    if not tool_config:
        return Config()

    return Config.from_dict(tool_config)


def get_default_ignores() -> list[str]:
    """Return default ignore patterns."""
    return [
        "__pycache__",
        "*.pyc",
        ".git",
        ".venv",
        "venv",
        "node_modules",
        ".tox",
        ".nox",
        ".eggs",
        "*.egg-info",
        "dist",
        "build",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
    ]
