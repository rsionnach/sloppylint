"""Axis 1: Information Utility (Noise) patterns."""

import re

from sloppy.patterns.base import RegexPattern, Severity
from sloppy.patterns.helpers import is_in_string_or_comment


class DebugPrint(RegexPattern):
    """Detect debug print statements."""

    id = "debug_print"
    severity = Severity.MEDIUM
    axis = "noise"
    message = "Debug print statement - remove before production"
    pattern = re.compile(r"\bprint\s*\(", re.IGNORECASE)

    # Files where print() is expected (CLI tools)
    CLI_FILE_PATTERNS = {"cli.py", "__main__.py", "main.py", "console.py", "commands.py"}

    def check_line(self, line: str, lineno: int, file) -> list:
        """Check line, excluding matches inside strings or comments."""
        if self.pattern is None:
            return []

        # Skip CLI-related files where print() is expected
        if file.name in self.CLI_FILE_PATTERNS:
            return []

        issues = []
        for match in self.pattern.finditer(line):
            if is_in_string_or_comment(line, match.start()):
                continue
            issues.append(
                self.create_issue(file=file, line=lineno, column=match.start(), code=line.strip())
            )
        return issues


class DebugBreakpoint(RegexPattern):
    """Detect breakpoint() and pdb calls."""

    id = "debug_breakpoint"
    severity = Severity.HIGH
    axis = "noise"
    message = "Debug breakpoint - remove before production"
    pattern = re.compile(r"\b(breakpoint\s*\(|pdb\.set_trace\s*\(|import\s+pdb)")


class RedundantComment(RegexPattern):
    """Detect comments that just restate the code."""

    id = "redundant_comment"
    severity = Severity.MEDIUM
    axis = "noise"
    message = "Redundant comment restating obvious code"
    pattern = re.compile(
        r"#\s*(increment|decrement|set|assign|return|get|initialize|init|create)\s+\w+\s*$",
        re.IGNORECASE,
    )


class EmptyDocstring(RegexPattern):
    """Detect empty or placeholder docstrings."""

    id = "empty_docstring"
    severity = Severity.MEDIUM
    axis = "noise"
    message = "Empty or placeholder docstring"
    pattern = re.compile(r'"""(\s*|\s*TODO.*|\s*FIXME.*|\s*pass\s*|\s*\.\.\.\s*)"""', re.IGNORECASE)


class GenericDocstring(RegexPattern):
    """Detect non-informative generic docstrings."""

    id = "generic_docstring"
    severity = Severity.LOW
    axis = "noise"
    message = "Generic docstring provides no useful information"
    pattern = re.compile(
        r'"""(This (function|method|class) (does|is|handles?|returns?|takes?) (stuff|things|something|it|the)\.?)"""',
        re.IGNORECASE,
    )


class CommentedCodeBlock(RegexPattern):
    """Detect large blocks of commented-out code."""

    id = "commented_code_block"
    severity = Severity.MEDIUM
    axis = "noise"
    message = "Commented-out code block - remove or uncomment"
    pattern = re.compile(
        r"^#\s*(def |class |import |from |if |for |while |return |yield )",
    )


class ChangelogComment(RegexPattern):
    """Detect version history in comments."""

    id = "changelog_in_code"
    severity = Severity.LOW
    axis = "noise"
    message = "Version history belongs in git commits, not code comments"
    pattern = re.compile(
        r"#\s*v?\d+\.\d+.*[-:].*\b(added|fixed|changed|removed|updated)\b", re.IGNORECASE
    )


NOISE_PATTERNS = [
    DebugPrint(),
    DebugBreakpoint(),
    RedundantComment(),
    EmptyDocstring(),
    GenericDocstring(),
    CommentedCodeBlock(),
    ChangelogComment(),
]
