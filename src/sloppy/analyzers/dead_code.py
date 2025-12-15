"""Dead code detection - unused functions and classes."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set

from sloppy.patterns.base import Issue, Severity


@dataclass
class DefinitionInfo:
    """Information about a function/class definition."""

    name: str
    kind: str  # 'function', 'class', 'method'
    line: int
    column: int
    is_private: bool
    is_dunder: bool
    parent_class: str | None = None


class DeadCodeAnalyzer(ast.NodeVisitor):
    """Analyzes a file for unused functions and classes."""

    def __init__(self, file: Path, source: str):
        self.file = file
        self.source = source
        self.definitions: Dict[str, DefinitionInfo] = {}
        self.used_names: Set[str] = set()
        self.exported_names: Set[str] = set()  # Names in __all__
        self.current_class: str | None = None

        # Names that are commonly defined but used externally
        self.external_use_patterns = {
            # Test functions
            "test_",
            "Test",
            # Framework hooks
            "setUp",
            "tearDown",
            "setUpClass",
            "tearDownClass",
            "setup",
            "teardown",
            "setup_method",
            "teardown_method",
            # Pytest fixtures
            "pytest_",
            "conftest",
            # Django
            "get_queryset",
            "get_context_data",
            "form_valid",
            # Flask
            "before_request",
            "after_request",
            # Entry points
            "main",
            "cli",
            "app",
        }

        # Decorators that indicate external use
        self.external_decorators = {
            "pytest.fixture",
            "fixture",
            "pytest.mark",
            "mark",
            "app.route",
            "route",
            "get",
            "post",
            "put",
            "delete",
            "celery.task",
            "task",
            "property",
            "staticmethod",
            "classmethod",
            "abstractmethod",
            "abstractproperty",
            "overload",
            "lru_cache",
            "cache",
            "cached_property",
            "dataclass",
            "click.command",
            "command",
        }

    def analyze(self, tree: ast.AST) -> List[Issue]:
        """Analyze the AST and return dead code issues."""
        # First pass: extract __all__ exports
        self._extract_exports(tree)

        # Second pass: collect definitions and usages
        self.visit(tree)

        # Find unused definitions
        issues = []
        for name, info in self.definitions.items():
            # Skip private/dunder methods - they might be used externally
            if info.is_dunder:
                continue

            # Skip if name is used
            if name in self.used_names:
                continue

            # Skip if explicitly exported via __all__
            if info.name in self.exported_names:
                continue

            # Skip if matches external use patterns
            if self._matches_external_pattern(info.name):
                continue

            # For methods, check if class is used (method might be called via instance)
            if info.kind == "method" and info.parent_class:
                if info.parent_class in self.used_names:
                    continue

            # Report as potentially unused
            issues.append(
                Issue(
                    pattern_id="dead_code",
                    severity=Severity.MEDIUM,
                    axis="structure",
                    file=self.file,
                    line=info.line,
                    column=info.column,
                    message=f"Potentially unused {info.kind} '{info.name}'",
                    code=f"def {info.name}(...)" if info.kind != "class" else f"class {info.name}:",
                )
            )

        return issues

    def _extract_exports(self, tree: ast.AST) -> None:
        """Extract names from __all__ if defined."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        if isinstance(node.value, (ast.List, ast.Tuple)):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    self.exported_names.add(elt.value)
            elif isinstance(node, ast.AugAssign):
                if isinstance(node.target, ast.Name) and node.target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                self.exported_names.add(elt.value)

    def _matches_external_pattern(self, name: str) -> bool:
        """Check if name matches patterns that suggest external use."""
        for pattern in self.external_use_patterns:
            if name.startswith(pattern) or name.endswith(pattern):
                return True
        return False

    def _has_external_decorator(self, decorators: List[ast.expr]) -> bool:
        """Check if any decorator suggests external use."""
        for dec in decorators:
            dec_name = self._get_decorator_name(dec)
            if dec_name:
                for pattern in self.external_decorators:
                    if pattern in dec_name:
                        return True
        return False

    def _get_decorator_name(self, dec: ast.expr) -> str | None:
        """Extract decorator name from AST node."""
        if isinstance(dec, ast.Name):
            return dec.id
        elif isinstance(dec, ast.Attribute):
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

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Track function definitions."""
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Track async function definitions."""
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Handle function/method definitions."""
        # Check for decorators that suggest external use
        if self._has_external_decorator(node.decorator_list):
            self.used_names.add(node.name)
        else:
            is_private = node.name.startswith("_") and not node.name.startswith("__")
            is_dunder = node.name.startswith("__") and node.name.endswith("__")

            kind = "method" if self.current_class else "function"

            # Don't track if it's a special method
            if not is_dunder:
                key = f"{self.current_class}.{node.name}" if self.current_class else node.name
                self.definitions[key] = DefinitionInfo(
                    name=node.name,
                    kind=kind,
                    line=node.lineno,
                    column=node.col_offset,
                    is_private=is_private,
                    is_dunder=is_dunder,
                    parent_class=self.current_class,
                )

        # Visit decorators for name usage
        for dec in node.decorator_list:
            self.visit(dec)

        # Visit body
        for stmt in node.body:
            self.visit(stmt)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Track class definitions."""
        # Check for decorators that suggest external use
        if self._has_external_decorator(node.decorator_list):
            self.used_names.add(node.name)
        else:
            is_private = node.name.startswith("_") and not node.name.startswith("__")

            self.definitions[node.name] = DefinitionInfo(
                name=node.name,
                kind="class",
                line=node.lineno,
                column=node.col_offset,
                is_private=is_private,
                is_dunder=False,
            )

        # Track base classes as used
        for base in node.bases:
            self.visit(base)

        # Visit decorators
        for dec in node.decorator_list:
            self.visit(dec)

        # Visit class body with class context
        old_class = self.current_class
        self.current_class = node.name
        for stmt in node.body:
            self.visit(stmt)
        self.current_class = old_class

    def visit_Name(self, node: ast.Name) -> None:
        """Track name usage."""
        self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Track attribute access."""
        # Track method calls like obj.method()
        self.used_names.add(node.attr)

        # Also track the base
        current = node
        while isinstance(current, ast.Attribute):
            current = current.value
        if isinstance(current, ast.Name):
            self.used_names.add(current.id)

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Track function/method calls."""
        if isinstance(node.func, ast.Name):
            self.used_names.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self.used_names.add(node.func.attr)

        self.generic_visit(node)


def find_dead_code(file: Path, source: str) -> List[Issue]:
    """Find dead code (unused functions/classes) in a Python file."""
    try:
        tree = ast.parse(source, filename=str(file))
    except SyntaxError:
        return []

    analyzer = DeadCodeAnalyzer(file, source)
    return analyzer.analyze(tree)
