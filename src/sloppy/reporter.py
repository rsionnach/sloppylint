"""Output reporters for terminal and JSON."""

import json
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

# Try to import rich for colored output
try:
    from rich import box
    from rich.console import Console
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

if TYPE_CHECKING:
    from sloppy.patterns.base import Issue
    from sloppy.scoring import SlopScore


# Severity colors for rich output
SEVERITY_COLORS = {
    "critical": "bold red",
    "high": "red",
    "medium": "yellow",
    "low": "blue",
}

SEVERITY_ICONS = {
    "critical": "[X]",
    "high": "[!]",
    "medium": "[~]",
    "low": "[-]",
}


class Reporter(ABC):
    """Base reporter class."""

    @abstractmethod
    def report(self, issues: list["Issue"], score: "SlopScore") -> None:
        """Report issues and score."""
        pass


class TerminalReporter(Reporter):
    """Terminal output reporter with optional rich formatting."""

    def __init__(
        self, format_style: str = "detailed", min_severity: str = "low", use_rich: bool = True
    ):
        self.format_style = format_style
        self.min_severity = min_severity
        self.use_rich = use_rich and RICH_AVAILABLE and sys.stdout.isatty()

        if self.use_rich:
            self.console = Console()

    def report(self, issues: list["Issue"], score: "SlopScore") -> None:
        """Print report to terminal."""
        if self.use_rich:
            self._report_rich(issues, score)
        else:
            self._report_plain(issues, score)

    def _report_rich(self, issues: list["Issue"], score: "SlopScore") -> None:
        """Print rich formatted report."""
        console = self.console

        if not issues:
            console.print("[bold green]No issues found. Clean code![/bold green]")
            self._print_score_rich(score)
            return

        # Group by severity
        by_severity = self._group_by_severity(issues)

        # Print issues by severity
        for severity in ["critical", "high", "medium", "low"]:
            severity_issues = by_severity[severity]
            if not severity_issues:
                continue

            color = SEVERITY_COLORS[severity]
            icon = SEVERITY_ICONS[severity]

            console.print()
            console.print(
                f"[{color}]{icon} {severity.upper()} ({len(severity_issues)} issues)[/{color}]"
            )
            console.print("[dim]" + "─" * 60 + "[/dim]")

            for issue in severity_issues[:20]:
                self._print_issue_rich(issue, color)

            if len(severity_issues) > 20:
                console.print(f"  [dim]... and {len(severity_issues) - 20} more[/dim]")

        self._print_score_rich(score)

    def _print_issue_rich(self, issue: "Issue", color: str) -> None:
        """Print a single issue with rich formatting."""
        location = f"{issue.file.name}:{issue.line}"

        if self.format_style == "compact":
            self.console.print(
                f"  [{color}]{location}[/{color}]  {issue.pattern_id}: {issue.message}"
            )
        else:
            self.console.print(f"  [{color}]{location}[/{color}]  [bold]{issue.pattern_id}[/bold]")
            self.console.print(f"    [dim]{issue.message}[/dim]")
            if issue.code:
                self.console.print(f"    [cyan]> {issue.code[:80]}[/cyan]")

    def _print_score_rich(self, score: "SlopScore") -> None:
        """Print the score summary with rich formatting."""
        console = self.console

        # Create score table
        table = Table(
            title="SLOPPY INDEX",
            box=box.ROUNDED,
            show_header=False,
            title_style="bold",
            border_style="dim",
        )
        table.add_column("Category", style="dim")
        table.add_column("Score", justify="right")

        table.add_row("Information Utility (Noise)", f"{score.noise} pts")
        table.add_row("Information Quality (Lies)", f"{score.quality} pts")
        table.add_row("Style / Taste (Soul)", f"{score.style} pts")
        table.add_row("Structural Issues", f"{score.structure} pts")
        table.add_row("─" * 30, "─" * 10, style="dim")
        table.add_row("[bold]TOTAL SLOP SCORE[/bold]", f"[bold]{score.total} pts[/bold]")

        console.print()
        console.print(table)

        # Verdict with color
        verdict_color = (
            "green"
            if score.verdict == "CLEAN"
            else "yellow"
            if score.verdict == "ACCEPTABLE"
            else "red"
        )
        console.print()
        console.print(f"Verdict: [{verdict_color} bold]{score.verdict}[/{verdict_color} bold]")

    def _report_plain(self, issues: list["Issue"], score: "SlopScore") -> None:
        """Print plain text report (no colors)."""
        if not issues:
            print("No issues found. Clean code!")
            self._print_score_plain(score)
            return

        # Group by severity
        by_severity = self._group_by_severity(issues)

        # Print issues by severity
        for severity in ["critical", "high", "medium", "low"]:
            severity_issues = by_severity[severity]
            if not severity_issues:
                continue

            print(f"\n{severity.upper()} ({len(severity_issues)} issues)")
            print("=" * 60)

            for issue in severity_issues[:20]:
                self._print_issue_plain(issue)

            if len(severity_issues) > 20:
                print(f"  ... and {len(severity_issues) - 20} more")

        self._print_score_plain(score)

    def _print_issue_plain(self, issue: "Issue") -> None:
        """Print a single issue in plain text."""
        location = f"{issue.file}:{issue.line}"
        if self.format_style == "compact":
            print(f"  {location}  {issue.pattern_id}: {issue.message}")
        else:
            print(f"  {location}  {issue.pattern_id}")
            print(f"    {issue.message}")
            if issue.code:
                print(f"    > {issue.code[:80]}")

    def _print_score_plain(self, score: "SlopScore") -> None:
        """Print the score summary in plain text."""
        print("\n")
        print("SLOPPY INDEX")
        print("=" * 50)
        print(f"Information Utility (Noise)    : {score.noise} pts")
        print(f"Information Quality (Lies)     : {score.quality} pts")
        print(f"Style / Taste (Soul)           : {score.style} pts")
        print(f"Structural Issues              : {score.structure} pts")
        print("-" * 50)
        print(f"TOTAL SLOP SCORE               : {score.total} pts")
        print()
        print(f"Verdict: {score.verdict}")

    def _group_by_severity(self, issues: list["Issue"]) -> dict[str, list["Issue"]]:
        """Group issues by severity level."""
        by_severity: dict[str, list[Issue]] = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
        }
        for issue in issues:
            by_severity[issue.severity.value].append(issue)
        return by_severity


class JSONReporter(Reporter):
    """JSON output reporter."""

    def report(self, issues: list["Issue"], score: "SlopScore") -> None:
        """Print JSON to stdout."""
        data = self._build_report(issues, score)
        print(json.dumps(data, indent=2))

    def write_file(self, issues: list["Issue"], score: "SlopScore", path: str) -> None:
        """Write JSON to file."""
        data = self._build_report(issues, score)
        Path(path).write_text(json.dumps(data, indent=2))

    def _build_report(self, issues: list["Issue"], score: "SlopScore") -> dict[str, object]:
        """Build the JSON report structure."""
        return {
            "summary": {
                "total_issues": len(issues),
                "score": {
                    "noise": score.noise,
                    "quality": score.quality,
                    "style": score.style,
                    "structure": score.structure,
                    "total": score.total,
                },
                "verdict": score.verdict,
            },
            "issues": [
                {
                    "pattern_id": issue.pattern_id,
                    "severity": issue.severity.value,
                    "axis": issue.axis,
                    "file": str(issue.file),
                    "line": issue.line,
                    "column": issue.column,
                    "message": issue.message,
                    "code": issue.code,
                }
                for issue in issues
            ],
        }
