"""Axis 1: Information Utility (Noise) patterns."""

import re

from sloppy.patterns.base import RegexPattern, Severity


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
    RedundantComment(),
    EmptyDocstring(),
    GenericDocstring(),
    ChangelogComment(),
]
