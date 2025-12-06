"""Axis 1: Information Utility (Noise) patterns."""

import re
from sloppy.patterns.base import RegexPattern, Severity


class DebugPrint(RegexPattern):
    """Detect debug print statements."""
    
    id = "debug_print"
    severity = Severity.MEDIUM
    axis = "noise"
    message = "Debug print statement - remove before production"
    pattern = re.compile(r'\bprint\s*\(', re.IGNORECASE)
    
    def check_line(self, line: str, lineno: int, file) -> list:
        """Check line, excluding matches inside strings."""
        if self.pattern is None:
            return []
        
        issues = []
        for match in self.pattern.finditer(line):
            # Check if match is inside a string
            start = match.start()
            prefix = line[:start]
            single_quotes = prefix.count("'") - prefix.count("\\'")
            double_quotes = prefix.count('"') - prefix.count('\\"')
            if single_quotes % 2 == 1 or double_quotes % 2 == 1:
                continue
            
            issues.append(self.create_issue(
                file=file, line=lineno, column=match.start(), code=line.strip()
            ))
        return issues


class DebugBreakpoint(RegexPattern):
    """Detect breakpoint() and pdb calls."""
    
    id = "debug_breakpoint"
    severity = Severity.HIGH
    axis = "noise"
    message = "Debug breakpoint - remove before production"
    pattern = re.compile(r'\b(breakpoint\s*\(|pdb\.set_trace\s*\(|import\s+pdb)')


class RedundantComment(RegexPattern):
    """Detect comments that just restate the code."""
    
    id = "redundant_comment"
    severity = Severity.MEDIUM
    axis = "noise"
    message = "Redundant comment restating obvious code"
    pattern = re.compile(
        r'#\s*(increment|decrement|set|assign|return|get|initialize|init|create)\s+\w+\s*$',
        re.IGNORECASE
    )


class EmptyDocstring(RegexPattern):
    """Detect empty or placeholder docstrings."""
    
    id = "empty_docstring"
    severity = Severity.MEDIUM
    axis = "noise"
    message = "Empty or placeholder docstring"
    pattern = re.compile(
        r'"""(\s*|\s*TODO.*|\s*FIXME.*|\s*pass\s*|\s*\.\.\.\s*)"""',
        re.IGNORECASE
    )


class GenericDocstring(RegexPattern):
    """Detect non-informative generic docstrings."""
    
    id = "generic_docstring"
    severity = Severity.LOW
    axis = "noise"
    message = "Generic docstring provides no useful information"
    pattern = re.compile(
        r'"""(This (function|method|class) (does|is|handles?|returns?|takes?) (stuff|things|something|it|the)\.?)"""',
        re.IGNORECASE
    )


class CommentedCodeBlock(RegexPattern):
    """Detect large blocks of commented-out code."""
    
    id = "commented_code_block"
    severity = Severity.MEDIUM
    axis = "noise"
    message = "Commented-out code block - remove or uncomment"
    pattern = re.compile(
        r'^#\s*(def |class |import |from |if |for |while |return |yield )',
    )


class ChangelogComment(RegexPattern):
    """Detect version history in comments."""
    
    id = "changelog_in_code"
    severity = Severity.LOW
    axis = "noise"
    message = "Version history belongs in git commits, not code comments"
    pattern = re.compile(
        r'#\s*v?\d+\.\d+.*[-:].*\b(added|fixed|changed|removed|updated)\b',
        re.IGNORECASE
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
