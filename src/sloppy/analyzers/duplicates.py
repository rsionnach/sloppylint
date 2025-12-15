"""Cross-file duplicate code detection."""

from __future__ import annotations

import ast
import hashlib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from sloppy.patterns.base import Issue, Severity


@dataclass
class CodeBlock:
    """A block of code (function or class) that can be compared."""

    name: str
    kind: str  # 'function', 'class'
    file: Path
    line: int
    code_hash: str
    line_count: int
    normalized_code: str


class DuplicateDetector:
    """Detects duplicate code blocks across multiple files."""

    MIN_LINES = 5  # Minimum lines for a block to be considered

    def __init__(self):
        self.blocks: List[CodeBlock] = []

    def add_file(self, file: Path, source: str) -> None:
        """Extract code blocks from a file."""
        try:
            tree = ast.parse(source, filename=str(file))
        except SyntaxError:
            return

        lines = source.splitlines()

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                block = self._extract_function_block(node, file, lines)
                if block:
                    self.blocks.append(block)
            elif isinstance(node, ast.ClassDef):
                block = self._extract_class_block(node, file, lines)
                if block:
                    self.blocks.append(block)

    def _extract_function_block(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        file: Path,
        lines: List[str],
    ) -> CodeBlock | None:
        """Extract and normalize a function block."""
        # Skip small functions
        end_line = self._get_end_line(node)
        line_count = end_line - node.lineno + 1

        if line_count < self.MIN_LINES:
            return None

        # Skip test functions
        if node.name.startswith("test_"):
            return None

        # Get the source code
        code_lines = lines[node.lineno - 1 : end_line]

        # Normalize the code for comparison
        normalized = self._normalize_function(node)

        return CodeBlock(
            name=node.name,
            kind="function",
            file=file,
            line=node.lineno,
            code_hash=hashlib.md5(normalized.encode()).hexdigest(),
            line_count=line_count,
            normalized_code=normalized,
        )

    def _extract_class_block(
        self,
        node: ast.ClassDef,
        file: Path,
        lines: List[str],
    ) -> CodeBlock | None:
        """Extract and normalize a class block."""
        end_line = self._get_end_line(node)
        line_count = end_line - node.lineno + 1

        if line_count < self.MIN_LINES:
            return None

        # Skip test classes
        if node.name.startswith("Test"):
            return None

        # Normalize the code for comparison
        normalized = self._normalize_class(node)

        return CodeBlock(
            name=node.name,
            kind="class",
            file=file,
            line=node.lineno,
            code_hash=hashlib.md5(normalized.encode()).hexdigest(),
            line_count=line_count,
            normalized_code=normalized,
        )

    def _get_end_line(self, node: ast.AST) -> int:
        """Get the end line of an AST node."""
        end_line = getattr(node, "end_lineno", node.lineno)

        # Recursively check children for max end line
        for child in ast.walk(node):
            child_end = getattr(child, "end_lineno", None)
            if child_end:
                end_line = max(end_line, child_end)

        return end_line

    def _normalize_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        """Normalize a function for comparison (ignore names, focus on structure and semantics)."""
        # Create a simplified representation of the function body
        parts = []

        # Normalize arguments (count and annotation types)
        arg_count = len(node.args.args)
        arg_types = []
        for arg in node.args.args:
            if arg.annotation:
                arg_types.append(self._get_annotation_repr(arg.annotation))
            else:
                arg_types.append("any")
        parts.append(f"args:{arg_count}:{','.join(arg_types)}")

        # Include return annotation if present
        if node.returns:
            parts.append(f"returns:{self._get_annotation_repr(node.returns)}")

        # Normalize body statements
        for stmt in node.body:
            parts.append(self._normalize_stmt(stmt))

        return "\n".join(parts)

    def _get_annotation_repr(self, annotation: ast.AST) -> str:
        """Get a string representation of a type annotation."""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Constant):
            return str(annotation.value)
        elif isinstance(annotation, ast.Subscript):
            base = self._get_annotation_repr(annotation.value)
            slice_repr = self._get_annotation_repr(annotation.slice)
            return f"{base}[{slice_repr}]"
        elif isinstance(annotation, ast.Attribute):
            return annotation.attr
        elif isinstance(annotation, ast.Tuple):
            elts = [self._get_annotation_repr(e) for e in annotation.elts]
            return f"({','.join(elts)})"
        return "unknown"

    def _normalize_class(self, node: ast.ClassDef) -> str:
        """Normalize a class for comparison."""
        parts = []

        # Count base classes
        parts.append(f"bases:{len(node.bases)}")

        # Normalize methods
        for stmt in node.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                parts.append(f"method:{self._normalize_function(stmt)}")
            else:
                parts.append(self._normalize_stmt(stmt))

        return "\n".join(parts)

    def _normalize_stmt(self, stmt: ast.AST, depth: int = 0) -> str:
        """Normalize a statement for comparison with semantic info."""
        prefix = "  " * depth

        if isinstance(stmt, ast.Return):
            ret_type = self._get_expr_signature(stmt.value) if stmt.value else "none"
            return f"{prefix}return:{ret_type}"
        elif isinstance(stmt, ast.If):
            cond_sig = self._get_expr_signature(stmt.test)
            parts = [f"{prefix}if:{cond_sig}"]
            for s in stmt.body:
                parts.append(self._normalize_stmt(s, depth + 1))
            if stmt.orelse:
                parts.append(f"{prefix}else")
                for s in stmt.orelse:
                    parts.append(self._normalize_stmt(s, depth + 1))
            return "\n".join(parts)
        elif isinstance(stmt, ast.For):
            iter_sig = self._get_expr_signature(stmt.iter)
            parts = [f"{prefix}for:{iter_sig}"]
            for s in stmt.body:
                parts.append(self._normalize_stmt(s, depth + 1))
            return "\n".join(parts)
        elif isinstance(stmt, ast.While):
            cond_sig = self._get_expr_signature(stmt.test)
            parts = [f"{prefix}while:{cond_sig}"]
            for s in stmt.body:
                parts.append(self._normalize_stmt(s, depth + 1))
            return "\n".join(parts)
        elif isinstance(stmt, ast.Try):
            parts = [f"{prefix}try"]
            for s in stmt.body:
                parts.append(self._normalize_stmt(s, depth + 1))
            for handler in stmt.handlers:
                exc_type = "bare"
                if handler.type:
                    exc_type = self._get_expr_signature(handler.type)
                parts.append(f"{prefix}except:{exc_type}")
                for s in handler.body:
                    parts.append(self._normalize_stmt(s, depth + 1))
            return "\n".join(parts)
        elif isinstance(stmt, ast.With):
            items_sig = ",".join(self._get_expr_signature(item.context_expr) for item in stmt.items)
            parts = [f"{prefix}with:{items_sig}"]
            for s in stmt.body:
                parts.append(self._normalize_stmt(s, depth + 1))
            return "\n".join(parts)
        elif isinstance(stmt, ast.Assign):
            val_sig = self._get_expr_signature(stmt.value)
            return f"{prefix}assign:{len(stmt.targets)}:{val_sig}"
        elif isinstance(stmt, ast.AugAssign):
            op_name = stmt.op.__class__.__name__
            val_sig = self._get_expr_signature(stmt.value)
            return f"{prefix}augassign:{op_name}:{val_sig}"
        elif isinstance(stmt, ast.Expr):
            expr_sig = self._get_expr_signature(stmt.value)
            return f"{prefix}expr:{expr_sig}"
        elif isinstance(stmt, ast.Pass):
            return f"{prefix}pass"
        elif isinstance(stmt, ast.Raise):
            exc_sig = self._get_expr_signature(stmt.exc) if stmt.exc else "none"
            return f"{prefix}raise:{exc_sig}"
        elif isinstance(stmt, ast.Assert):
            test_sig = self._get_expr_signature(stmt.test)
            return f"{prefix}assert:{test_sig}"
        else:
            return f"{prefix}{stmt.__class__.__name__.lower()}"

    def _get_expr_signature(self, expr: ast.AST | None) -> str:
        """Get a signature for an expression that captures its semantic type."""
        if expr is None:
            return "none"
        if isinstance(expr, ast.Call):
            func_name = self._get_call_name(expr)
            arg_count = len(expr.args) + len(expr.keywords)
            return f"call:{func_name}:{arg_count}"
        elif isinstance(expr, ast.BinOp):
            op_name = expr.op.__class__.__name__
            return f"binop:{op_name}"
        elif isinstance(expr, ast.UnaryOp):
            op_name = expr.op.__class__.__name__
            return f"unaryop:{op_name}"
        elif isinstance(expr, ast.Compare):
            ops = ",".join(op.__class__.__name__ for op in expr.ops)
            return f"compare:{ops}"
        elif isinstance(expr, ast.BoolOp):
            op_name = expr.op.__class__.__name__
            return f"boolop:{op_name}:{len(expr.values)}"
        elif isinstance(expr, ast.Constant):
            return f"const:{type(expr.value).__name__}"
        elif isinstance(expr, ast.List):
            return f"list:{len(expr.elts)}"
        elif isinstance(expr, ast.Dict):
            return f"dict:{len(expr.keys)}"
        elif isinstance(expr, ast.Set):
            return f"set:{len(expr.elts)}"
        elif isinstance(expr, ast.Tuple):
            return f"tuple:{len(expr.elts)}"
        elif isinstance(expr, ast.Name):
            return "name"
        elif isinstance(expr, ast.Attribute):
            return f"attr:{expr.attr}"
        elif isinstance(expr, ast.Subscript):
            return "subscript"
        elif isinstance(expr, ast.ListComp):
            return f"listcomp:{len(expr.generators)}"
        elif isinstance(expr, ast.DictComp):
            return f"dictcomp:{len(expr.generators)}"
        elif isinstance(expr, ast.SetComp):
            return f"setcomp:{len(expr.generators)}"
        elif isinstance(expr, ast.GeneratorExp):
            return f"genexp:{len(expr.generators)}"
        elif isinstance(expr, ast.IfExp):
            return "ifexp"
        elif isinstance(expr, ast.Lambda):
            return f"lambda:{len(expr.args.args)}"
        return expr.__class__.__name__.lower()

    def _get_call_name(self, call: ast.Call) -> str:
        """Extract the function/method name from a call."""
        if isinstance(call.func, ast.Name):
            return call.func.id
        elif isinstance(call.func, ast.Attribute):
            return call.func.attr
        return "unknown"

    def find_duplicates(self) -> List[Issue]:
        """Find duplicate code blocks and return issues."""
        # Group blocks by hash
        by_hash: Dict[str, List[CodeBlock]] = defaultdict(list)
        for block in self.blocks:
            by_hash[block.code_hash].append(block)

        issues = []
        seen_pairs: set = set()

        for code_hash, blocks in by_hash.items():
            if len(blocks) < 2:
                continue

            # Report duplicates
            for i, block1 in enumerate(blocks):
                for block2 in blocks[i + 1 :]:
                    # Skip if same file (handled by other patterns)
                    if block1.file == block2.file:
                        continue

                    # Create unique pair key
                    pair_key = tuple(
                        sorted(
                            [
                                f"{block1.file}:{block1.line}",
                                f"{block2.file}:{block2.line}",
                            ]
                        )
                    )

                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)

                    # Report for the second occurrence
                    issues.append(
                        Issue(
                            pattern_id="duplicate_code",
                            severity=Severity.MEDIUM,
                            axis="structure",
                            file=block2.file,
                            line=block2.line,
                            column=0,
                            message=(
                                f"Duplicate {block2.kind} '{block2.name}' "
                                f"({block2.line_count} lines) - "
                                f"same as '{block1.name}' in {block1.file.name}:{block1.line}"
                            ),
                            code=(
                                f"def {block2.name}(...)"
                                if block2.kind == "function"
                                else f"class {block2.name}:"
                            ),
                        )
                    )

        return issues


def find_cross_file_duplicates(files: List[Tuple[Path, str]]) -> List[Issue]:
    """Find duplicate code across multiple files.

    Args:
        files: List of (path, source_content) tuples

    Returns:
        List of duplicate code issues
    """
    detector = DuplicateDetector()

    for file, source in files:
        detector.add_file(file, source)

    return detector.find_duplicates()
