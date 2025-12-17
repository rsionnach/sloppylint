"""Axis 3: Style/Taste (Soul) patterns - AI-specific comment patterns."""

from __future__ import annotations

import re

from sloppy.patterns.base import RegexPattern, Severity


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


STYLE_PATTERNS = [
    OverconfidentComment(),
    HedgingComment(),
    ApologeticComment(),
]
