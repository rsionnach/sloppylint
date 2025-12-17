"""Main detection orchestration."""

from __future__ import annotations

import ast
import fnmatch
import re
from pathlib import Path

from sloppy.analyzers.ast_analyzer import ASTAnalyzer
from sloppy.patterns import get_all_patterns
from sloppy.patterns.base import Issue
from sloppy.patterns.helpers import get_multiline_string_lines

SEVERITY_ORDER = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "critical": 3,
}


class Detector:
    """Main detector that orchestrates all pattern checks."""

    def __init__(
        self,
        ignore_patterns: list[str] | None = None,
        include_patterns: list[str] | None = None,
        disabled_patterns: list[str] | None = None,
        min_severity: str = "low",
        root_path: Path | None = None,
    ):
        self.ignore_patterns = ignore_patterns or []
        self.include_patterns = include_patterns or []
        self.disabled_patterns: set[str] = set(disabled_patterns or [])
        self.min_severity = min_severity
        self.min_severity_level = SEVERITY_ORDER.get(min_severity, 0)
        self.root_path = root_path or Path.cwd()

        # Load patterns
        self.patterns = [p for p in get_all_patterns() if p.id not in self.disabled_patterns]

    def scan(self, paths: list[Path]) -> list[Issue]:
        """Scan all paths and return issues."""
        issues: list[Issue] = []

        for path in paths:
            if path.is_file():
                if self._should_scan(path):
                    file_issues = self._scan_file(path)
                    issues.extend(file_issues)
            elif path.is_dir():
                for file_path in path.rglob("*.py"):
                    if self._should_scan(file_path):
                        file_issues = self._scan_file(file_path)
                        issues.extend(file_issues)

        # Filter by severity
        issues = [
            i for i in issues if SEVERITY_ORDER.get(i.severity.value, 0) >= self.min_severity_level
        ]

        # Sort by severity (critical first), then by file, then by line
        issues.sort(
            key=lambda i: (
                -SEVERITY_ORDER.get(i.severity.value, 0),
                i.file,
                i.line,
            )
        )

        return issues

    def _should_scan(self, path: Path) -> bool:
        """Check if a file should be scanned."""
        if path.suffix != ".py":
            return False

        # Convert to relative POSIX path for consistent matching across platforms
        rel_path = self._get_relative_posix_path(path)

        # Check ignore patterns
        for pattern in self.ignore_patterns:
            if self._match_pattern(rel_path, pattern):
                return False

        # Check include patterns (if specified, file must match at least one)
        if self.include_patterns:
            matched = any(
                self._match_pattern(rel_path, pattern) for pattern in self.include_patterns
            )
            if not matched:
                return False

        return True

    def _get_relative_posix_path(self, path: Path) -> str:
        """Convert path to relative POSIX-style string for consistent matching."""
        try:
            rel_path = path.resolve().relative_to(self.root_path.resolve())
        except ValueError:
            # Path is not relative to root, use absolute path
            rel_path = path.resolve()
        return rel_path.as_posix()

    def _match_pattern(self, path_str: str, pattern: str) -> bool:
        """Match path against a glob pattern using fnmatch.

        Handles ** patterns for recursive matching.
        All matching is done against POSIX-style relative paths.
        """
        # Normalize pattern to POSIX style
        pattern = pattern.replace("\\", "/")

        # Handle ** patterns (recursive match)
        if "**" in pattern:
            # Convert ** to match any number of path segments
            # e.g., "src/**/*.py" matches "src/a/b/c.py"
            # Escape special regex chars except * and ?
            regex_pattern = re.escape(pattern)
            # Convert ** to match any path segments (including none)
            regex_pattern = regex_pattern.replace(r"\*\*", ".*")
            # Convert remaining * to match anything except /
            regex_pattern = regex_pattern.replace(r"\*", "[^/]*")
            # Convert ? to match single char except /
            regex_pattern = regex_pattern.replace(r"\?", "[^/]")
            regex_pattern = f"^{regex_pattern}$"

            return bool(re.match(regex_pattern, path_str))

        # Simple fnmatch for patterns without **
        return fnmatch.fnmatch(path_str, pattern)

    def _scan_file(self, path: Path) -> list[Issue]:
        """Scan a single file."""
        issues: list[Issue] = []

        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return issues

        # Parse AST
        try:
            tree = ast.parse(content, filename=str(path))
        except SyntaxError:
            return issues

        # Run AST analyzer
        analyzer = ASTAnalyzer(path, content, self.patterns)
        issues.extend(analyzer.analyze(tree))

        # Get multi-line string locations for accurate string detection
        multiline_string_lines = get_multiline_string_lines(content)

        # Set multi-line context on patterns before line-based checks
        for pattern in self.patterns:
            pattern.multiline_string_lines = multiline_string_lines

        # Run line-based patterns
        lines = content.splitlines()
        for pattern in self.patterns:
            if hasattr(pattern, "check_line"):
                for lineno, line in enumerate(lines, start=1):
                    pattern_issues = pattern.check_line(line, lineno, path)
                    issues.extend(pattern_issues)

        return issues
