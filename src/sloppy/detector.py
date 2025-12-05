"""Main detection orchestration."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterator, List, Optional, Set

from sloppy.patterns import get_all_patterns
from sloppy.patterns.base import Issue, Severity
from sloppy.analyzers.ast_analyzer import ASTAnalyzer
from sloppy.analyzers.unused_imports import find_unused_imports
from sloppy.analyzers.dead_code import find_dead_code


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
        ignore_patterns: Optional[List[str]] = None,
        disabled_patterns: Optional[List[str]] = None,
        min_severity: str = "low",
    ):
        self.ignore_patterns = ignore_patterns or []
        self.disabled_patterns: Set[str] = set(disabled_patterns or [])
        self.min_severity = min_severity
        self.min_severity_level = SEVERITY_ORDER.get(min_severity, 0)
        
        # Load patterns
        self.patterns = [
            p for p in get_all_patterns()
            if p.id not in self.disabled_patterns
        ]
    
    def scan(self, paths: List[Path]) -> List[Issue]:
        """Scan all paths and return issues."""
        issues: list[Issue] = []
        
        for path in paths:
            if path.is_file():
                if self._should_scan(path):
                    issues.extend(self._scan_file(path))
            elif path.is_dir():
                issues.extend(self._scan_directory(path))
        
        # Filter by severity
        issues = [
            i for i in issues
            if SEVERITY_ORDER.get(i.severity.value, 0) >= self.min_severity_level
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
    
    def _scan_directory(self, directory: Path) -> Iterator[Issue]:
        """Recursively scan a directory."""
        for path in directory.rglob("*.py"):
            if self._should_scan(path):
                yield from self._scan_file(path)
    
    def _should_scan(self, path: Path) -> bool:
        """Check if a file should be scanned."""
        if not path.suffix == ".py":
            return False
        
        # Check ignore patterns
        path_str = str(path)
        for pattern in self.ignore_patterns:
            if path.match(pattern):
                return False
        
        return True
    
    def _scan_file(self, path: Path) -> List[Issue]:
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
        
        # Run line-based patterns
        lines = content.splitlines()
        for pattern in self.patterns:
            if hasattr(pattern, "check_line"):
                for lineno, line in enumerate(lines, start=1):
                    pattern_issues = pattern.check_line(line, lineno, path)
                    issues.extend(pattern_issues)
        
        # Run file-level analyzers
        if "unused_import" not in self.disabled_patterns:
            issues.extend(find_unused_imports(path, content))
        
        if "dead_code" not in self.disabled_patterns:
            issues.extend(find_dead_code(path, content))
        
        return issues
