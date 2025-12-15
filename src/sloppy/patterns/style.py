"""Axis 3: Style/Taste (Soul) patterns."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import List

from sloppy.patterns.base import ASTPattern, Issue, RegexPattern, Severity
from sloppy.patterns.helpers import is_in_string_or_comment


class OverconfidentComment(RegexPattern):
    """Detect overconfident comments indicating false certainty."""

    id = "overconfident_comment"
    severity = Severity.MEDIUM
    axis = "style"
    message = "Overconfident comment - verify claim before shipping"
    pattern = re.compile(
        r"#\s*(obviously|clearly|simply|just|easy|trivial|basically|of course|naturally)\b",
        re.IGNORECASE,
    )


class HedgingComment(RegexPattern):
    """Detect hedging comments indicating uncertainty."""

    id = "hedging_comment"
    severity = Severity.HIGH
    axis = "style"
    message = "Hedging comment suggests uncertainty - verify code works"
    pattern = re.compile(
        r"#\s*(should work|hopefully|probably|might work|try this|i think|seems to|appears to)\b",
        re.IGNORECASE,
    )


class ApologeticComment(RegexPattern):
    """Detect apologetic comments."""

    id = "apologetic_comment"
    severity = Severity.MEDIUM
    axis = "style"
    message = "Apologetic comment - fix the issue instead of apologizing"
    pattern = re.compile(
        r"#\s*(sorry|hack|hacky|ugly|bad|terrible|awful|gross|yuck|forgive)\b", re.IGNORECASE
    )


class OverlongLine(RegexPattern):
    """Detect lines over 120 characters."""

    id = "overlong_line"
    severity = Severity.LOW
    axis = "style"
    message = "Line exceeds 120 characters"
    pattern = re.compile(r"^.{121,}$")


class MultipleStatements(RegexPattern):
    """Detect multiple statements on one line."""

    id = "multiple_statements"
    severity = Severity.LOW
    axis = "style"
    message = "Multiple statements on one line - split for readability"
    pattern = re.compile(r";\s*\w+\s*=")  # var = x; var = y pattern


class GodFunction(ASTPattern):
    """Detect functions that are too long or have too many parameters."""

    id = "god_function"
    severity = Severity.HIGH
    axis = "style"
    message = "God function - too long or too many parameters"
    node_types = (ast.FunctionDef, ast.AsyncFunctionDef)

    MAX_LINES = 50
    MAX_PARAMS = 5
    MAX_PARAMS_INIT = 10  # Higher threshold for __init__ methods

    def check_node(
        self,
        node: ast.AST,
        file: Path,
        source_lines: List[str],
    ) -> List[Issue]:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return []

        issues = []

        # Check line count
        if hasattr(node, "end_lineno") and node.end_lineno:
            line_count = node.end_lineno - node.lineno + 1
            if line_count > self.MAX_LINES:
                issues.append(
                    self.create_issue_from_node(
                        node,
                        file,
                        code=f"def {node.name}(...)",
                        message=f"Function has {line_count} lines (max {self.MAX_LINES})",
                    )
                )

        # Check parameter count
        args = node.args
        param_count = (
            len(args.args)
            + len(args.posonlyargs)
            + len(args.kwonlyargs)
            + (1 if args.vararg else 0)
            + (1 if args.kwarg else 0)
        )
        # Subtract self/cls for methods
        if args.args and args.args[0].arg in ("self", "cls"):
            param_count -= 1

        # Use higher threshold for __init__ and __new__
        max_params = self.MAX_PARAMS_INIT if node.name in ("__init__", "__new__") else self.MAX_PARAMS

        if param_count > max_params:
            issues.append(
                self.create_issue_from_node(
                    node,
                    file,
                    code=f"def {node.name}(...)",
                    message=f"Function has {param_count} parameters (max {max_params})",
                )
            )

        return issues


class DeepNesting(ASTPattern):
    """Detect deeply nested code."""

    id = "deep_nesting"
    severity = Severity.MEDIUM
    axis = "style"
    message = "Code is deeply nested - consider extracting to functions"
    node_types = (ast.If, ast.For, ast.While, ast.With, ast.Try)

    MAX_DEPTH = 4

    def check_node(
        self,
        node: ast.AST,
        file: Path,
        source_lines: List[str],
    ) -> List[Issue]:
        # This is handled specially in the analyzer to track depth
        return []


class NestedTernary(RegexPattern):
    """Detect nested ternary expressions."""

    id = "nested_ternary"
    severity = Severity.MEDIUM
    axis = "style"
    message = "Nested ternary expression - use if/else for clarity"
    pattern = re.compile(
        r"\bif\b[^:]+\belse\b[^:]+\bif\b[^:]+\belse\b",
    )

    def check_line(self, line: str, lineno: int, file) -> list:
        """Check line, excluding matches inside strings or comments."""
        if self.pattern is None:
            return []

        issues = []
        for match in self.pattern.finditer(line):
            if is_in_string_or_comment(line, match.start()):
                continue
            issues.append(
                self.create_issue(file=file, line=lineno, column=match.start(), code=line.strip())
            )
        return issues


STYLE_PATTERNS = [
    OverconfidentComment(),
    HedgingComment(),
    ApologeticComment(),
    OverlongLine(),
    MultipleStatements(),
    GodFunction(),
    DeepNesting(),
    NestedTernary(),
]
