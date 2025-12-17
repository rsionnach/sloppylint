"""Axis 2: Information Quality (Hallucinations) patterns."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from sloppy.patterns.base import ASTPattern, Issue, RegexPattern, Severity


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
        source_lines: list[str],
    ) -> list[Issue]:
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
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, source_lines: list[str]
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
        source_lines: list[str],
    ) -> list[Issue]:
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
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, source_lines: list[str]
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
        source_lines: list[str],
    ) -> list[Issue]:
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
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, source_lines: list[str]
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
        source_lines: list[str],
    ) -> list[Issue]:
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
        source_lines: list[str],
    ) -> list[Issue]:
        from sloppy.analyzers.import_validator import is_likely_hallucinated_package

        issues = []

        if isinstance(node, ast.Import):
            for alias in node.names:
                error_msg = is_likely_hallucinated_package(alias.name, source_file=file)
                if error_msg:
                    issues.append(
                        self.create_issue_from_node(
                            node,
                            file,
                            code=f"import {alias.name}",
                            message=error_msg,
                        )
                    )

        elif isinstance(node, ast.ImportFrom) and node.module:
            error_msg = is_likely_hallucinated_package(node.module, source_file=file)
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
        source_lines: list[str],
    ) -> list[Issue]:
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
        source_lines: list[str],
    ) -> list[Issue]:
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
    PassPlaceholder(),
    EllipsisPlaceholder(),
    NotImplementedPlaceholder(),
    HallucinatedImport(),
    WrongStdlibImport(),
    HallucinatedMethod(),
    HallucinatedAttribute(),
]
