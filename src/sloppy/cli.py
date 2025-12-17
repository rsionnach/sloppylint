"""Command-line interface for Sloppy."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sloppy import __version__
from sloppy.config import get_default_ignores, load_config
from sloppy.detector import Detector
from sloppy.reporter import JSONReporter, TerminalReporter
from sloppy.scoring import calculate_score


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="sloppylint",
        description="Python AI Slop Detector - Find over-engineering, hallucinations, and dead code",
    )

    parser.add_argument(
        "paths",
        nargs="*",
        default=["."],
        help="Files or directories to scan (default: current directory)",
    )

    parser.add_argument(
        "--output",
        "-o",
        metavar="FILE",
        help="Write JSON report to FILE",
    )

    parser.add_argument(
        "--format",
        "-f",
        choices=["compact", "detailed", "json"],
        default="detailed",
        help="Output format (default: detailed)",
    )

    parser.add_argument(
        "--severity",
        "-s",
        choices=["low", "medium", "high", "critical"],
        default="low",
        help="Minimum severity to report (default: low)",
    )

    parser.add_argument(
        "--ignore",
        "-i",
        action="append",
        default=[],
        metavar="PATTERN",
        help="Glob pattern to exclude (can be repeated)",
    )

    parser.add_argument(
        "--include",
        "-I",
        action="append",
        default=[],
        metavar="PATTERN",
        help="Only scan files matching glob pattern (can be repeated)",
    )

    parser.add_argument(
        "--disable",
        "-d",
        action="append",
        default=[],
        metavar="PATTERN_ID",
        help="Disable specific pattern by ID (can be repeated)",
    )

    strictness = parser.add_mutually_exclusive_group()
    strictness.add_argument(
        "--strict",
        action="store_true",
        help="Report all severities including low",
    )
    strictness.add_argument(
        "--lenient",
        action="store_true",
        help="Only report critical and high severity",
    )

    parser.add_argument(
        "--ci",
        action="store_true",
        help="CI mode: exit with code 1 if issues found",
    )

    parser.add_argument(
        "--strict-imports",
        action="store_true",
        dest="strict_imports",
        help="Check imports against installed packages (may cause false positives)",
    )

    parser.add_argument(
        "--max-score",
        type=int,
        metavar="N",
        help="Exit with code 1 if slop score exceeds N",
    )

    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    return parser


def main(args: list[str] | None = None) -> int:
    """Main entry point."""
    parser = create_parser()
    opts = parser.parse_args(args)

    # Load config from pyproject.toml
    config = load_config()

    # Merge CLI args into config (CLI takes precedence)
    config.merge_cli_args(opts)

    # Determine severity threshold
    if opts.strict:
        min_severity = "low"
    elif opts.lenient:
        min_severity = "high"
    else:
        min_severity = config.severity

    # Build ignore patterns (defaults + config + cli)
    ignore_patterns = get_default_ignores() + config.ignore

    # Build include patterns (config + cli)
    include_patterns = config.include

    # Create detector and scan
    detector = Detector(
        ignore_patterns=ignore_patterns,
        include_patterns=include_patterns,
        disabled_patterns=config.disable,
        min_severity=min_severity,
    )

    # Collect all paths
    paths = [Path(p) for p in opts.paths]

    # Run detection
    issues = detector.scan(paths)

    # Calculate score
    score = calculate_score(issues)

    # Report results
    if config.format == "json" or opts.output:
        json_reporter = JSONReporter()
        json_reporter.report(issues, score)
    else:
        terminal_reporter = TerminalReporter(
            format_style=config.format,
            min_severity=min_severity,
        )
        terminal_reporter.report(issues, score)

    # Write JSON output if requested
    if opts.output:
        json_reporter = JSONReporter()
        json_reporter.write_file(issues, score, opts.output)

    # Determine exit code
    exit_code = 0
    if config.ci and issues:
        exit_code = 1
    if config.max_score is not None and score.total > config.max_score:
        exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
