"""Unused imports detection via AST analysis."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

from sloppy.patterns.base import Issue, Severity


@dataclass
class ImportInfo:
    """Information about an import."""

    name: str  # The name as used in code (could be alias)
    module: str  # The module being imported from
    original_name: str  # The original name if aliased
    line: int
    column: int
    is_star: bool = False


class UnusedImportAnalyzer(ast.NodeVisitor):
    """Analyzes a file for unused imports."""

    def __init__(self, file: Path, source: str):
        self.file = file
        self.source = source
        self.imports: Dict[str, ImportInfo] = {}  # name -> ImportInfo
        self.used_names: Set[str] = set()
        self.star_imports: List[ImportInfo] = []

        # Names that are commonly imported but used implicitly
        self.implicit_uses = {
            "TYPE_CHECKING",  # Used in if TYPE_CHECKING blocks
            "annotations",  # from __future__ import annotations
            "Optional",
            "Union",
            "List",
            "Dict",
            "Set",
            "Tuple",  # Type hints
            "Any",
            "Callable",
            "Type",
            "TypeVar",
            "Generic",
            "overload",
            "final",
            "ClassVar",
            "Protocol",
        }

    def analyze(self, tree: ast.AST) -> List[Issue]:
        """Analyze the AST and return unused import issues."""
        # First pass: collect imports
        self.visit(tree)

        # Find unused imports
        issues = []
        for name, info in self.imports.items():
            if name not in self.used_names and name not in self.implicit_uses:
                # Check if it might be used in a string annotation
                if not self._is_used_in_string_annotation(name):
                    issues.append(
                        Issue(
                            pattern_id="unused_import",
                            severity=Severity.MEDIUM,
                            axis="structure",
                            file=self.file,
                            line=info.line,
                            column=info.column,
                            message=f"Unused import '{name}'"
                            + (f" (from {info.module})" if info.module != name else ""),
                            code=self._get_import_code(info),
                        )
                    )

        return issues

    def _get_import_code(self, info: ImportInfo) -> str:
        """Generate the import statement code."""
        if info.module == info.original_name:
            return f"import {info.name}"
        elif info.name != info.original_name:
            return f"from {info.module} import {info.original_name} as {info.name}"
        else:
            return f"from {info.module} import {info.name}"

    def _is_used_in_string_annotation(self, name: str) -> bool:
        """Check if a name might be used in a string type annotation."""
        # Simple heuristic: check if the name appears in the source as a string
        return f"'{name}'" in self.source or f'"{name}"' in self.source

    def visit_Import(self, node: ast.Import) -> None:
        """Handle 'import x' statements."""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            # For 'import a.b.c', only 'a' is accessible
            base_name = name.split(".")[0]
            self.imports[base_name] = ImportInfo(
                name=base_name,
                module=alias.name,
                original_name=alias.name,
                line=node.lineno,
                column=node.col_offset,
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Handle 'from x import y' statements."""
        module = node.module or ""

        for alias in node.names:
            if alias.name == "*":
                self.star_imports.append(
                    ImportInfo(
                        name="*",
                        module=module,
                        original_name="*",
                        line=node.lineno,
                        column=node.col_offset,
                        is_star=True,
                    )
                )
                continue

            name = alias.asname if alias.asname else alias.name
            self.imports[name] = ImportInfo(
                name=name,
                module=module,
                original_name=alias.name,
                line=node.lineno,
                column=node.col_offset,
            )

        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        """Track name usage."""
        self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Track attribute access - the base name is used."""
        # Get the root name for chained attributes like a.b.c
        current = node
        while isinstance(current, ast.Attribute):
            current = current.value
        if isinstance(current, ast.Name):
            self.used_names.add(current.id)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Track function definitions and their annotations."""
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Track async function definitions and their annotations."""
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Handle function definitions - check decorators and annotations."""
        # Check decorators
        for decorator in node.decorator_list:
            self.visit(decorator)

        # Check argument annotations
        for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
            if arg.annotation:
                self._extract_annotation_names(arg.annotation)

        if node.args.vararg and node.args.vararg.annotation:
            self._extract_annotation_names(node.args.vararg.annotation)
        if node.args.kwarg and node.args.kwarg.annotation:
            self._extract_annotation_names(node.args.kwarg.annotation)

        # Check argument default values (e.g., FastAPI Depends)
        for default in node.args.defaults:
            self.visit(default)
        for default in node.args.kw_defaults:
            if default:
                self.visit(default)

        # Check return annotation
        if node.returns:
            self._extract_annotation_names(node.returns)

        # Visit body
        for stmt in node.body:
            self.visit(stmt)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Track annotated assignments."""
        self._extract_annotation_names(node.annotation)
        if node.value:
            self.visit(node.value)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Track class definitions."""
        # Check base classes
        for base in node.bases:
            self.visit(base)

        # Check decorators
        for decorator in node.decorator_list:
            self.visit(decorator)

        # Visit body
        for stmt in node.body:
            self.visit(stmt)

    def _extract_annotation_names(self, annotation: ast.AST) -> None:
        """Extract names used in type annotations."""
        if isinstance(annotation, ast.Name):
            self.used_names.add(annotation.id)
        elif isinstance(annotation, ast.Attribute):
            # For things like typing.Optional
            current = annotation
            while isinstance(current, ast.Attribute):
                current = current.value
            if isinstance(current, ast.Name):
                self.used_names.add(current.id)
        elif isinstance(annotation, ast.Subscript):
            # For things like List[int], Optional[str]
            self._extract_annotation_names(annotation.value)
            self._extract_annotation_names(annotation.slice)
        elif isinstance(annotation, ast.Tuple):
            for elt in annotation.elts:
                self._extract_annotation_names(elt)
        elif isinstance(annotation, ast.BinOp):
            # For Union types with | syntax (Python 3.10+)
            self._extract_annotation_names(annotation.left)
            self._extract_annotation_names(annotation.right)
        elif isinstance(annotation, ast.Constant):
            # String annotations like "ForwardRef"
            if isinstance(annotation.value, str):
                # Try to extract name from string
                self.used_names.add(annotation.value.split("[")[0].strip())


def find_unused_imports(file: Path, source: str) -> List[Issue]:
    """Find unused imports in a Python file."""
    try:
        tree = ast.parse(source, filename=str(file))
    except SyntaxError:
        return []

    analyzer = UnusedImportAnalyzer(file, source)
    return analyzer.analyze(tree)
