"""Structural anti-pattern detection."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Set

from sloppy.patterns.base import ASTPattern, Issue, Severity


class BareExcept(ASTPattern):
    """Detect bare except clauses."""

    id = "bare_except"
    severity = Severity.CRITICAL
    axis = "structure"
    message = "Bare except catches everything including SystemExit and KeyboardInterrupt"
    node_types = (ast.ExceptHandler,)

    def check_node(
        self,
        node: ast.AST,
        file: Path,
        source_lines: List[str],
    ) -> List[Issue]:
        if not isinstance(node, ast.ExceptHandler):
            return []

        if node.type is None:
            return [self.create_issue_from_node(node, file, code="except:")]

        return []


class BroadExcept(ASTPattern):
    """Detect overly broad exception handling."""

    id = "broad_except"
    severity = Severity.HIGH
    axis = "structure"
    message = "Broad exception handling - catch specific exceptions instead"
    node_types = (ast.ExceptHandler,)

    BROAD_EXCEPTIONS = {"Exception", "BaseException"}

    def check_node(
        self,
        node: ast.AST,
        file: Path,
        source_lines: List[str],
    ) -> List[Issue]:
        if not isinstance(node, ast.ExceptHandler):
            return []

        if node.type is None:
            return []  # Handled by BareExcept

        exc_name = None
        if isinstance(node.type, ast.Name):
            exc_name = node.type.id
        elif isinstance(node.type, ast.Attribute):
            exc_name = node.type.attr

        if exc_name in self.BROAD_EXCEPTIONS:
            return [self.create_issue_from_node(node, file, code=f"except {exc_name}:")]

        return []


class EmptyExcept(ASTPattern):
    """Detect except blocks that just pass."""

    id = "empty_except"
    severity = Severity.HIGH
    axis = "structure"
    message = "Exception swallowed with pass - at minimum log the error"
    node_types = (ast.ExceptHandler,)

    def check_node(
        self,
        node: ast.AST,
        file: Path,
        source_lines: List[str],
    ) -> List[Issue]:
        if not isinstance(node, ast.ExceptHandler):
            return []

        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            exc_name = "..."
            if node.type:
                if isinstance(node.type, ast.Name):
                    exc_name = node.type.id
            return [self.create_issue_from_node(node, file, code=f"except {exc_name}: pass")]

        return []


class StarImport(ASTPattern):
    """Detect wildcard imports."""

    id = "star_import"
    severity = Severity.HIGH
    axis = "structure"
    message = "Wildcard import pollutes namespace - import specific names"
    node_types = (ast.ImportFrom,)

    def check_node(
        self,
        node: ast.AST,
        file: Path,
        source_lines: List[str],
    ) -> List[Issue]:
        if not isinstance(node, ast.ImportFrom):
            return []

        for alias in node.names:
            if alias.name == "*":
                module = node.module or ""
                return [self.create_issue_from_node(node, file, code=f"from {module} import *")]

        return []


class SingleMethodClass(ASTPattern):
    """Detect classes with only one method besides __init__."""

    id = "single_method_class"
    severity = Severity.HIGH
    axis = "structure"
    message = "Single-method class could be a function instead"
    node_types = (ast.ClassDef,)

    SPECIAL_METHODS = {"__init__", "__new__", "__del__", "__repr__", "__str__"}

    # Base classes that indicate interface/protocol patterns where single methods are valid
    INTERFACE_BASES = {
        "Protocol",
        "ABC",
        "ABCMeta",
        "Interface",
        "Generic",
        "TypedDict",
        "NamedTuple",
        "Enum",
        "IntEnum",
        "StrEnum",
        "Flag",
        "IntFlag",
        "Exception",
        "BaseException",
    }

    # Decorators that indicate special class patterns
    SPECIAL_DECORATORS = {
        "dataclass",
        "dataclasses.dataclass",
        "attrs",
        "attr.s",
        "attr.attrs",
        "define",
        "attr.define",
        "frozen",
        "attr.frozen",
        "runtime_checkable",
        "typing.runtime_checkable",
        "final",
        "typing.final",
    }

    def check_node(
        self,
        node: ast.AST,
        file: Path,
        source_lines: List[str],
    ) -> List[Issue]:
        if not isinstance(node, ast.ClassDef):
            return []

        # Skip Protocol/ABC/interface classes
        if self._is_interface_class(node):
            return []

        # Skip classes with special decorators
        if self._has_special_decorator(node):
            return []

        # Skip classes that inherit from non-trivial base classes (part of a hierarchy)
        if self._has_significant_base(node):
            return []

        # Count non-special methods
        methods = [
            n
            for n in node.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and n.name not in self.SPECIAL_METHODS
            and not n.name.startswith("_")
        ]

        # Count special methods
        special = [
            n
            for n in node.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and n.name in self.SPECIAL_METHODS
        ]

        # Flag if only one public method (besides __init__)
        if len(methods) == 1 and len(special) <= 1:
            return [
                self.create_issue_from_node(
                    node,
                    file,
                    code=f"class {node.name}: # single method: {methods[0].name}",
                    message=f"Class '{node.name}' has only one method '{methods[0].name}' - consider using a function",
                )
            ]

        return []

    def _is_interface_class(self, node: ast.ClassDef) -> bool:
        """Check if class inherits from Protocol, ABC, or similar interface bases."""
        for base in node.bases:
            base_name = self._get_base_name(base)
            if base_name in self.INTERFACE_BASES:
                return True
        # Also check keywords (e.g., class Foo(metaclass=ABCMeta))
        for keyword in node.keywords:
            if keyword.arg == "metaclass":
                meta_name = self._get_base_name(keyword.value)
                if meta_name in self.INTERFACE_BASES:
                    return True
        return False

    def _has_significant_base(self, node: ast.ClassDef) -> bool:
        """Check if class inherits from a non-trivial base class (part of hierarchy)."""
        # Skip if no bases or only has object
        if not node.bases:
            return False
        for base in node.bases:
            base_name = self._get_base_name(base)
            # If it has any base class other than object, it's part of a hierarchy
            if base_name and base_name not in ("object",):
                return True
        return False

    def _get_base_name(self, base: ast.AST) -> str | None:
        """Extract the base class name from AST node."""
        if isinstance(base, ast.Name):
            return base.id
        elif isinstance(base, ast.Attribute):
            return base.attr
        elif isinstance(base, ast.Subscript):
            # For Generic[T], Protocol[T], etc.
            return self._get_base_name(base.value)
        return None

    def _has_special_decorator(self, node: ast.ClassDef) -> bool:
        """Check if class has decorators that make single-method valid."""
        for dec in node.decorator_list:
            dec_name = self._get_decorator_name(dec)
            if dec_name in self.SPECIAL_DECORATORS:
                return True
        return False

    def _get_decorator_name(self, dec: ast.AST) -> str | None:
        """Extract decorator name from AST node."""
        if isinstance(dec, ast.Name):
            return dec.id
        elif isinstance(dec, ast.Attribute):
            # For things like dataclasses.dataclass
            parts = []
            current = dec
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        elif isinstance(dec, ast.Call):
            return self._get_decorator_name(dec.func)
        return None


class UnreachableCode(ASTPattern):
    """Detect code after return/raise statements."""

    id = "unreachable_code"
    severity = Severity.MEDIUM
    axis = "structure"
    message = "Unreachable code after return/raise"
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

        def check_body(body: list[ast.stmt]) -> None:
            for i, stmt in enumerate(body):
                if isinstance(stmt, (ast.Return, ast.Raise)):
                    # Check if there are more statements after
                    if i < len(body) - 1:
                        next_stmt = body[i + 1]
                        issues.append(
                            self.create_issue(
                                file=file,
                                line=getattr(next_stmt, "lineno", 0),
                                column=getattr(next_stmt, "col_offset", 0),
                                message="Code after return/raise is unreachable",
                            )
                        )

                # Recurse into nested blocks
                if isinstance(stmt, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                    for child in ast.iter_child_nodes(stmt):
                        if isinstance(child, list):
                            check_body(child)

        check_body(node.body)
        return issues


STRUCTURE_PATTERNS = [
    BareExcept(),
    BroadExcept(),
    EmptyExcept(),
    StarImport(),
    SingleMethodClass(),
    UnreachableCode(),
]
