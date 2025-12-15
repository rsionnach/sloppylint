"""Axis 2: Information Quality (Hallucinations) patterns."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import List

from sloppy.patterns.base import ASTPattern, Issue, RegexPattern, Severity
from sloppy.patterns.helpers import is_in_string_or_comment


class TodoPlaceholder(RegexPattern):
    """Detect TODO/FIXME implementation placeholders."""

    id = "todo_placeholder"
    severity = Severity.HIGH
    axis = "quality"
    message = "TODO placeholder - implementation needed"
    pattern = re.compile(
        r"#\s*(TODO|FIXME|XXX|HACK)\s*:?\s*.*(implement|add|finish|complete|fill in|your code|logic here)",
        re.IGNORECASE,
    )


class AssumptionComment(RegexPattern):
    """Detect assumption comments indicating unverified code."""

    id = "assumption_comment"
    severity = Severity.HIGH
    axis = "quality"
    message = "Assumption in code - verify before shipping"
    pattern = re.compile(
        r"#\s*(assuming|assumes?|presumably|apparently|i think|we think|should be|might be)\b",
        re.IGNORECASE,
    )


class MagicNumber(RegexPattern):
    """Detect unexplained magic numbers."""

    id = "magic_number"
    severity = Severity.MEDIUM
    axis = "quality"
    message = "Magic number - extract to named constant"
    pattern = re.compile(
        r"(?<![.\w])\b(?!0\b|1\b|2\b|100\b|1000\b|True\b|False\b|None\b)"
        r"\d{2,}\b(?!\.\d)"  # 2+ digit numbers not followed by decimal
    )

    # Well-known constants that don't need extraction
    WELL_KNOWN_NUMBERS = {
        # HTTP status codes
        "200", "201", "202", "204",  # Success
        "301", "302", "303", "304", "307", "308",  # Redirects
        "400", "401", "403", "404", "405", "409", "410", "422", "429",  # Client errors
        "500", "501", "502", "503", "504",  # Server errors
        # Time units
        "24", "60", "365", "366",  # hours/day, minutes/seconds, days/year
        # Computing
        "256", "512", "1024", "2048", "4096", "8192", "16384", "32768", "65536",  # Powers of 2
        "8080", "443", "80",  # Common ports
        # Common defaults
        "10", "50", "99", "128", "255",
    }

    def check_line(
        self,
        line: str,
        lineno: int,
        file: Path,
    ) -> List[Issue]:
        """Check a line for magic numbers, excluding those in strings/comments."""
        if self.pattern is None:
            return []

        # Skip dunder assignments (like __copyright__, __version__)
        stripped = line.strip()
        if stripped.startswith("__") and "=" in stripped:
            return []

        issues = []
        for match in self.pattern.finditer(line):
            if is_in_string_or_comment(line, match.start()):
                continue
            # Skip well-known numbers
            if match.group() in self.WELL_KNOWN_NUMBERS:
                continue
            issues.append(
                self.create_issue(
                    file=file,
                    line=lineno,
                    column=match.start(),
                    code=line.strip(),
                )
            )

        return issues


class PassPlaceholder(ASTPattern):
    """Detect placeholder functions with just pass."""

    id = "pass_placeholder"
    severity = Severity.HIGH
    axis = "quality"
    message = "Placeholder function with pass - implementation needed"
    node_types = (ast.FunctionDef, ast.AsyncFunctionDef)

    ABSTRACT_DECORATORS = {
        "abstractmethod",
        "abstractproperty",
        "abstractclassmethod",
        "abstractstaticmethod",
        "overload",
    }

    def check_node(
        self,
        node: ast.AST,
        file: Path,
        source_lines: List[str],
    ) -> List[Issue]:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return []

        # Skip if has abstract/overload decorator
        if self._has_abstract_decorator(node):
            return []

        # Skip if likely a Protocol/ABC method
        if self._is_likely_protocol_method(node, source_lines):
            return []

        # Check if body is just pass (optionally with docstring)
        body = node.body
        if len(body) == 1 and isinstance(body[0], ast.Pass):
            return [self.create_issue_from_node(node, file, code=f"def {node.name}(...): pass")]

        # Docstring + pass
        if len(body) == 2:
            has_docstring = (
                isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            )
            if has_docstring and isinstance(body[1], ast.Pass):
                return [self.create_issue_from_node(node, file, code=f"def {node.name}(...): pass")]

        return []

    def _has_abstract_decorator(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        """Check if function has an abstract or overload decorator."""
        for dec in node.decorator_list:
            dec_name = None
            if isinstance(dec, ast.Name):
                dec_name = dec.id
            elif isinstance(dec, ast.Attribute):
                dec_name = dec.attr
            elif isinstance(dec, ast.Call):
                if isinstance(dec.func, ast.Name):
                    dec_name = dec.func.id
                elif isinstance(dec.func, ast.Attribute):
                    dec_name = dec.func.attr
            if dec_name in self.ABSTRACT_DECORATORS:
                return True
        return False

    def _is_likely_protocol_method(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, source_lines: List[str]
    ) -> bool:
        """Check if function is likely a method inside a Protocol/ABC class."""
        args = node.args.args
        if not args:
            return False
        first_arg = args[0].arg
        if first_arg not in ("self", "cls"):
            return False

        func_line = node.lineno - 1
        for i in range(func_line - 1, max(func_line - 50, -1), -1):
            if i < 0 or i >= len(source_lines):
                continue
            line = source_lines[i].strip()
            if line.startswith("class ") and ":" in line:
                if any(
                    base in line
                    for base in ("Protocol", "ABC", "ABCMeta", "Interface", "typing_extensions")
                ):
                    return True
                break
        return False


class EllipsisPlaceholder(ASTPattern):
    """Detect placeholder functions with just ellipsis."""

    id = "ellipsis_placeholder"
    severity = Severity.HIGH
    axis = "quality"
    message = "Placeholder function with ... - implementation needed"
    node_types = (ast.FunctionDef, ast.AsyncFunctionDef)

    # Decorators that indicate abstract/protocol methods where ... is valid
    ABSTRACT_DECORATORS = {
        "abstractmethod",
        "abstractproperty",
        "abstractclassmethod",
        "abstractstaticmethod",
        "overload",
    }

    def check_node(
        self,
        node: ast.AST,
        file: Path,
        source_lines: List[str],
    ) -> List[Issue]:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return []

        # Skip if has abstract/overload decorator
        if self._has_abstract_decorator(node):
            return []

        # Skip if likely a Protocol/ABC method
        if self._is_likely_protocol_method(node, source_lines):
            return []

        body = node.body

        # Just ellipsis
        if len(body) == 1:
            if isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                if body[0].value.value is ...:
                    return [
                        self.create_issue_from_node(node, file, code=f"def {node.name}(...): ...")
                    ]

        # Docstring + ellipsis
        if len(body) == 2:
            has_docstring = (
                isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            )
            if has_docstring and isinstance(body[1], ast.Expr):
                if isinstance(body[1].value, ast.Constant) and body[1].value.value is ...:
                    return [
                        self.create_issue_from_node(node, file, code=f"def {node.name}(...): ...")
                    ]

        return []

    def _has_abstract_decorator(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        """Check if function has an abstract or overload decorator."""
        for dec in node.decorator_list:
            dec_name = None
            if isinstance(dec, ast.Name):
                dec_name = dec.id
            elif isinstance(dec, ast.Attribute):
                dec_name = dec.attr
            elif isinstance(dec, ast.Call):
                if isinstance(dec.func, ast.Name):
                    dec_name = dec.func.id
                elif isinstance(dec.func, ast.Attribute):
                    dec_name = dec.func.attr
            if dec_name in self.ABSTRACT_DECORATORS:
                return True
        return False

    def _is_likely_protocol_method(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, source_lines: List[str]
    ) -> bool:
        """Check if function is likely a method inside a Protocol/ABC class."""
        # Check if it's a method (first arg is self/cls)
        args = node.args.args
        if not args:
            return False
        first_arg = args[0].arg
        if first_arg not in ("self", "cls"):
            return False

        # Look backwards in source to find class definition
        func_line = node.lineno - 1
        for i in range(func_line - 1, max(func_line - 50, -1), -1):
            if i < 0 or i >= len(source_lines):
                continue
            line = source_lines[i].strip()
            # Check for class definition with Protocol/ABC base
            if line.startswith("class ") and ":" in line:
                # Check if it inherits from Protocol, ABC, or similar
                if any(
                    base in line
                    for base in ("Protocol", "ABC", "ABCMeta", "Interface", "typing_extensions")
                ):
                    return True
                # Stop at first class definition found
                break
        return False


class NotImplementedPlaceholder(ASTPattern):
    """Detect placeholder functions that just raise NotImplementedError."""

    id = "notimplemented_placeholder"
    severity = Severity.MEDIUM
    axis = "quality"
    message = "Function raises NotImplementedError - implementation needed"
    node_types = (ast.FunctionDef, ast.AsyncFunctionDef)

    ABSTRACT_DECORATORS = {
        "abstractmethod",
        "abstractproperty",
        "abstractclassmethod",
        "abstractstaticmethod",
        "overload",
    }

    def check_node(
        self,
        node: ast.AST,
        file: Path,
        source_lines: List[str],
    ) -> List[Issue]:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return []

        # Skip if has abstract/overload decorator
        if self._has_abstract_decorator(node):
            return []

        # Skip if likely a Protocol/ABC method
        if self._is_likely_protocol_method(node, source_lines):
            return []

        body = node.body

        # Check last statement for raise NotImplementedError
        effective_body = body
        if len(body) >= 1:
            # Skip docstring
            if isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                if isinstance(body[0].value.value, str):
                    effective_body = body[1:]

        if len(effective_body) == 1 and isinstance(effective_body[0], ast.Raise):
            exc = effective_body[0].exc
            if isinstance(exc, ast.Call):
                if isinstance(exc.func, ast.Name) and exc.func.id == "NotImplementedError":
                    return [
                        self.create_issue_from_node(
                            node, file, code=f"def {node.name}(...): raise NotImplementedError"
                        )
                    ]
            elif isinstance(exc, ast.Name) and exc.id == "NotImplementedError":
                return [
                    self.create_issue_from_node(
                        node, file, code=f"def {node.name}(...): raise NotImplementedError"
                    )
                ]

        return []

    def _has_abstract_decorator(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        """Check if function has an abstract or overload decorator."""
        for dec in node.decorator_list:
            dec_name = None
            if isinstance(dec, ast.Name):
                dec_name = dec.id
            elif isinstance(dec, ast.Attribute):
                dec_name = dec.attr
            elif isinstance(dec, ast.Call):
                if isinstance(dec.func, ast.Name):
                    dec_name = dec.func.id
                elif isinstance(dec.func, ast.Attribute):
                    dec_name = dec.func.attr
            if dec_name in self.ABSTRACT_DECORATORS:
                return True
        return False

    def _is_likely_protocol_method(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, source_lines: List[str]
    ) -> bool:
        """Check if function is likely a method inside a Protocol/ABC class."""
        args = node.args.args
        if not args:
            return False
        first_arg = args[0].arg
        if first_arg not in ("self", "cls"):
            return False

        func_line = node.lineno - 1
        for i in range(func_line - 1, max(func_line - 50, -1), -1):
            if i < 0 or i >= len(source_lines):
                continue
            line = source_lines[i].strip()
            if line.startswith("class ") and ":" in line:
                if any(
                    base in line
                    for base in ("Protocol", "ABC", "ABCMeta", "Interface", "typing_extensions")
                ):
                    return True
                break
        return False


class MutableDefaultArg(ASTPattern):
    """Detect mutable default arguments."""

    id = "mutable_default_arg"
    severity = Severity.CRITICAL
    axis = "quality"
    message = "Mutable default argument - use None and initialize inside function"
    node_types = (ast.FunctionDef, ast.AsyncFunctionDef)

    def check_node(
        self,
        node: ast.AST,
        file: Path,
        source_lines: List[str],
    ) -> List[Issue]:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return []

        issues = []

        # Check positional defaults
        for default in node.args.defaults:
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                issues.append(
                    self.create_issue_from_node(
                        default,
                        file,
                        code=f"def {node.name}(...={self._get_default_repr(default)})",
                        message=f"Mutable default argument ({self._get_default_repr(default)}) - use None instead",
                    )
                )

        # Check keyword-only defaults
        for default in node.args.kw_defaults:
            if default and isinstance(default, (ast.List, ast.Dict, ast.Set)):
                issues.append(
                    self.create_issue_from_node(
                        default,
                        file,
                        code=f"def {node.name}(...={self._get_default_repr(default)})",
                        message=f"Mutable default argument ({self._get_default_repr(default)}) - use None instead",
                    )
                )

        return issues

    def _get_default_repr(self, node: ast.AST) -> str:
        if isinstance(node, ast.List):
            return "[]"
        elif isinstance(node, ast.Dict):
            return "{}"
        elif isinstance(node, ast.Set):
            return "set()"
        return "..."


class HallucinatedImport(ASTPattern):
    """Detect imports from wrong modules (common AI hallucinations)."""

    id = "hallucinated_import"
    severity = Severity.CRITICAL
    axis = "quality"
    message = "Hallucinated import - name imported from wrong module"
    node_types = (ast.ImportFrom,)

    def check_node(
        self,
        node: ast.AST,
        file: Path,
        source_lines: List[str],
    ) -> List[Issue]:
        if not isinstance(node, ast.ImportFrom):
            return []

        if node.module is None:
            return []

        from sloppy.analyzers.import_validator import check_known_hallucination

        issues = []
        for alias in node.names:
            name = alias.name
            error_msg = check_known_hallucination(node.module, name)
            if error_msg:
                issues.append(
                    self.create_issue_from_node(
                        node,
                        file,
                        code=f"from {node.module} import {name}",
                        message=error_msg,
                    )
                )

        return issues


class WrongStdlibImport(ASTPattern):
    """Detect imports from non-existent standard library modules."""

    id = "wrong_stdlib_import"
    severity = Severity.CRITICAL
    axis = "quality"
    message = "Import from non-existent module"
    node_types = (ast.Import, ast.ImportFrom)

    def check_node(
        self,
        node: ast.AST,
        file: Path,
        source_lines: List[str],
    ) -> List[Issue]:
        from sloppy.analyzers.import_validator import is_likely_hallucinated_package

        issues = []

        if isinstance(node, ast.Import):
            for alias in node.names:
                error_msg = is_likely_hallucinated_package(alias.name)
                if error_msg:
                    issues.append(
                        self.create_issue_from_node(
                            node,
                            file,
                            code=f"import {alias.name}",
                            message=error_msg,
                        )
                    )

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                error_msg = is_likely_hallucinated_package(node.module)
                if error_msg:
                    names = ", ".join(a.name for a in node.names[:3])
                    if len(node.names) > 3:
                        names += ", ..."
                    issues.append(
                        self.create_issue_from_node(
                            node,
                            file,
                            code=f"from {node.module} import {names}",
                            message=error_msg,
                        )
                    )

        return issues


class HallucinatedMethod(ASTPattern):
    """Detect method calls that don't exist (JavaScript patterns, typos)."""

    id = "hallucinated_method"
    severity = Severity.HIGH
    axis = "quality"
    message = "Hallucinated method call - method does not exist in Python"
    node_types = (ast.Call,)

    def check_node(
        self,
        node: ast.AST,
        file: Path,
        source_lines: List[str],
    ) -> List[Issue]:
        if not isinstance(node, ast.Call):
            return []

        # Check if it's a method call (obj.method())
        if not isinstance(node.func, ast.Attribute):
            return []

        method_name = node.func.attr

        from sloppy.analyzers.import_validator import check_hallucinated_method

        error_msg = check_hallucinated_method(method_name)
        if error_msg:
            # Try to get the source line for context
            lineno = getattr(node, "lineno", 0)
            code = None
            if 0 < lineno <= len(source_lines):
                code = source_lines[lineno - 1].strip()

            return [
                self.create_issue_from_node(
                    node,
                    file,
                    code=code or f".{method_name}()",
                    message=error_msg,
                )
            ]

        return []


class HallucinatedAttribute(ASTPattern):
    """Detect attribute access that doesn't exist (like .length on list)."""

    id = "hallucinated_attribute"
    severity = Severity.HIGH
    axis = "quality"
    message = "Hallucinated attribute - attribute does not exist in Python"
    node_types = (ast.Attribute,)

    # Attributes from other languages that don't exist in Python
    INVALID_ATTRIBUTES = {
        # JavaScript
        "length": "Use len(obj) not obj.length - JavaScript pattern",
        "size": "Use len(obj) not obj.size - JavaScript pattern (unless pandas/set)",
        "prototype": "Python doesn't have prototypes - JavaScript pattern",
        "__proto__": "Python doesn't have __proto__ - JavaScript pattern",
        "constructor": "Use type(obj) or obj.__class__ - JavaScript pattern",
        # Java/C#
        "Length": "Use len(obj) not obj.Length - C# pattern",
        "Count": "Use len(obj) not obj.Count - C# pattern",
        # Go/Ruby
        "nil": "Use None not nil - Go/Ruby pattern",
        # Java/C#/JavaScript
        "null": "Use None not null - Java/C#/JS pattern",
    }

    def check_node(
        self,
        node: ast.AST,
        file: Path,
        source_lines: List[str],
    ) -> List[Issue]:
        if not isinstance(node, ast.Attribute):
            return []

        # Skip if this is a method call (handled by HallucinatedMethod)
        # We detect that by checking if this Attribute is the func of a Call
        # This is tricky at this level, so we check specific attributes

        attr_name = node.attr

        if attr_name in self.INVALID_ATTRIBUTES:
            # Try to get the source line for context
            lineno = getattr(node, "lineno", 0)
            code = None
            if 0 < lineno <= len(source_lines):
                code = source_lines[lineno - 1].strip()

            return [
                self.create_issue_from_node(
                    node,
                    file,
                    code=code or f".{attr_name}",
                    message=self.INVALID_ATTRIBUTES[attr_name],
                )
            ]

        return []


HALLUCINATION_PATTERNS = [
    TodoPlaceholder(),
    AssumptionComment(),
    MagicNumber(),
    PassPlaceholder(),
    EllipsisPlaceholder(),
    NotImplementedPlaceholder(),
    MutableDefaultArg(),
    HallucinatedImport(),
    WrongStdlibImport(),
    HallucinatedMethod(),
    HallucinatedAttribute(),
]
