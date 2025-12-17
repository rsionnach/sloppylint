"""Import validation for detecting hallucinated packages."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# Standard library modules (Python 3.9+)
STDLIB_MODULES: set[str] = (
    set(sys.stdlib_module_names)
    if hasattr(sys, "stdlib_module_names")
    else {
        "abc",
        "argparse",
        "ast",
        "asyncio",
        "base64",
        "collections",
        "configparser",
        "contextlib",
        "copy",
        "csv",
        "dataclasses",
        "datetime",
        "decimal",
        "difflib",
        "email",
        "enum",
        "functools",
        "glob",
        "hashlib",
        "html",
        "http",
        "importlib",
        "inspect",
        "io",
        "itertools",
        "json",
        "logging",
        "math",
        "multiprocessing",
        "operator",
        "os",
        "pathlib",
        "pickle",
        "platform",
        "pprint",
        "re",
        "shutil",
        "signal",
        "socket",
        "sqlite3",
        "string",
        "subprocess",
        "sys",
        "tempfile",
        "textwrap",
        "threading",
        "time",
        "traceback",
        "types",
        "typing",
        "unittest",
        "urllib",
        "uuid",
        "warnings",
        "weakref",
        "xml",
        "zipfile",
    }
)


def module_exists(module_name: str) -> bool:
    """Check if a module/package exists in the Python environment."""
    # Check stdlib first (fast path)
    base = module_name.split(".")[0]
    if base in STDLIB_MODULES:
        return True

    try:
        spec = importlib.util.find_spec(module_name)
        return spec is not None
    except (ModuleNotFoundError, ValueError, ImportError, AttributeError):
        return False
    except Exception:
        # Catch any other exceptions that might occur during module spec lookup
        # (e.g., pydantic v1 compatibility issues with Python 3.14+)
        return True  # Assume exists to avoid false positives


def validate_import(module_name: str, name: str | None = None) -> str | None:
    """
    Validate that an import is correct.

    Returns an error message if the import is invalid, None otherwise.
    """
    # Check known hallucinations first
    if name:
        hallucination_msg = check_known_hallucination(module_name, name)
        if hallucination_msg:
            return hallucination_msg

    # Check if base module exists
    base_module = module_name.split(".")[0]
    if not module_exists(base_module):
        return f"Module '{module_name}' does not exist"

    return None


# Common hallucinated imports (known bad patterns from AI)
# Format: (module, name) -> error message (None means valid)
KNOWN_HALLUCINATIONS = {
    # === FastAPI / Starlette confusion ===
    (
        "requests",
        "JSONResponse",
    ): "JSONResponse is from starlette.responses or fastapi.responses, not requests",
    ("requests", "Response"): None,  # Valid - requests has Response
    ("flask", "Query"): "Query is from fastapi, not flask",
    ("flask", "Depends"): "Depends is from fastapi, not flask",
    ("flask", "HTTPException"): None,  # Valid - flask.exceptions.HTTPException exists
    ("django", "FastAPI"): "FastAPI is its own package, not part of django",
    ("django", "APIRouter"): "APIRouter is from fastapi, not django",
    # === typing module confusion ===
    # NOTE: Many typing features were added in 3.10/3.11. We only flag imports that
    # are NEVER valid (true hallucinations), not version-dependent features.
    # Projects can use typing_extensions for backwards compatibility if needed.
    ("typing", "Required"): None,  # Valid in 3.11+, typing_extensions for earlier
    ("typing", "NotRequired"): None,  # Valid in 3.11+, typing_extensions for earlier
    ("typing", "Self"): None,  # Valid in 3.11+, typing_extensions for earlier
    ("typing", "TypeGuard"): None,  # Valid in 3.10+, typing_extensions for earlier
    ("typing", "ParamSpec"): None,  # Valid in 3.10+
    # === dataclasses confusion ===
    ("collections", "dataclass"): "dataclass is from dataclasses, not collections",
    ("typing", "dataclass"): "dataclass is from dataclasses, not typing",
    ("attrs", "dataclass"): "dataclass is from dataclasses; attrs uses @attr.s or @define",
    # === pydantic confusion ===
    ("dataclasses", "BaseModel"): "BaseModel is from pydantic, not dataclasses",
    ("typing", "BaseModel"): "BaseModel is from pydantic, not typing",
    ("dataclasses", "Field"): None,  # Valid - dataclasses has field()
    # === async confusion ===
    ("asyncio", "aiohttp"): "aiohttp is its own package, not part of asyncio",
    ("asyncio", "httpx"): "httpx is its own package, not part of asyncio",
    ("async", "await"): "async/await are keywords, not importable",
    # === os/pathlib confusion ===
    ("os", "makedirectory"): "Use os.makedirs() not os.makedirectory()",
    ("os", "makedir"): "Use os.mkdir() or os.makedirs(), not os.makedir()",
    ("os.path", "Path"): "Path is from pathlib, not os.path",
    ("pathlib", "mkdirs"): "Use Path.mkdir(parents=True), not mkdirs()",
    # === json confusion ===
    ("json", "JSONEncoder"): None,  # Valid
    ("json", "parse"): "Use json.loads() not json.parse() (JavaScript pattern)",
    ("json", "stringify"): "Use json.dumps() not json.stringify() (JavaScript pattern)",
    # NOTE: Generic module names like 'utils', 'helpers', 'common' are NOT flagged here
    # because they are often valid local modules. The WrongStdlibImport pattern
    # handles these with proper local file checking.
    # === pytest confusion ===
    ("unittest", "fixture"): "fixture is from pytest, not unittest",
    ("unittest", "mark"): "mark is from pytest, not unittest",
    ("pytest", "TestCase"): "TestCase is from unittest, not pytest",
    # === requests/urllib confusion ===
    ("urllib", "get"): "Use urllib.request.urlopen() or requests.get(), not urllib.get()",
    ("urllib", "post"): "Use urllib.request.urlopen() or requests.post(), not urllib.post()",
    ("http", "get"): "Use http.client or requests for HTTP requests",
    # === logging confusion ===
    ("logging", "log"): None,  # Valid - logging.log() exists
    # NOTE: We don't flag generic module names like 'utils', 'helpers', 'common' here
    # because they are often valid local modules. The WrongStdlibImport pattern
    # handles these with proper local file checking.
    # === SQLAlchemy confusion ===
    ("sqlalchemy", "Model"): "Model is from flask_sqlalchemy, SQLAlchemy uses declarative_base()",
    ("sqlalchemy", "db"): "db is typically a Flask-SQLAlchemy instance, not from sqlalchemy",
}


def check_known_hallucination(module: str, name: str | None) -> str | None:
    """Check if this is a known hallucinated import pattern."""
    # Check exact match
    if name is not None:
        result = KNOWN_HALLUCINATIONS.get((module, name))
        if result is not None:
            return result

    # Check module-only patterns (name=None in dict)
    # Use a cast since the dict has mixed None/str values
    key: tuple[str, str | None] = (module, None)
    module_only = KNOWN_HALLUCINATIONS.get(key)  # type: ignore[arg-type]
    if module_only is not None:
        return module_only

    return None


def is_likely_hallucinated_package(
    module_name: str,
    source_file: Path | None = None,
    strict: bool = False,
) -> str | None:
    """
    Check if a module name looks like a hallucinated package.

    Args:
        module_name: The module being imported
        source_file: Path to the file containing the import (for local file checking)
        strict: If True, also check if module exists in environment (may cause
                false positives for uninstalled dependencies)

    Returns error message if likely hallucinated, None otherwise.
    """

    base = module_name.split(".")[0]

    # Check if it's a local file in the same directory as the source file
    if source_file is not None:
        source_dir = source_file.parent
        # Check for module_name.py in same directory
        local_module = source_dir / f"{base}.py"
        if local_module.exists():
            return None
        # Check for module_name/ package directory
        local_package = source_dir / base
        if local_package.is_dir() and (local_package / "__init__.py").exists():
            return None
        # Check for relative imports - look for the module in parent directories
        # that might be package roots (have __init__.py)
        current = source_dir
        for _ in range(3):  # Look up to 3 levels
            if (current / f"{base}.py").exists():
                return None
            if (current / base).is_dir():
                return None
            parent = current.parent
            if parent == current:
                break
            # Only continue if current dir is a package
            if not (current / "__init__.py").exists():
                break
            current = parent

    # Check if it's a stdlib module (always valid)
    if base in STDLIB_MODULES:
        return None

    # In strict mode, check if the module exists in the environment
    # This may cause false positives for third-party packages not installed
    if strict:
        if module_exists(module_name):
            return None
        # In strict mode, flag missing modules
        return f"Module '{module_name}' not found in environment"

    # Non-strict mode (default): Only flag KNOWN AI hallucination patterns
    # This avoids false positives for legitimate third-party packages

    # Common AI hallucination patterns - these are generic names AI often invents
    # that don't exist as real packages
    hallucinated_patterns = {
        "utils": "Module 'utils' does not exist - did you mean a local module?",
        "helpers": "Module 'helpers' does not exist - did you mean a local module?",
        "common": "Module 'common' does not exist - did you mean a local module?",
    }

    if base in hallucinated_patterns:
        return hallucinated_patterns[base]

    # Don't flag unknown modules as hallucinations - they might be:
    # - Local modules we couldn't find
    # - Third-party packages not yet installed
    # - Typos (not AI hallucinations)
    return None


# Common hallucinated method calls
# Format: method_name -> (correct_method, context_hint)
# NOTE: Only include methods that are NEVER valid in Python. Methods like find(), sub(),
# push(), echo() are valid in certain contexts (str.find, re.sub, custom methods, click.echo)
# and should NOT be flagged as hallucinations.
HALLUCINATED_METHODS = {
    # String methods - only flag methods that don't exist on ANY Python type
    "titlecase": ("title", "str.title()"),
    "uppercase": ("upper", "str.upper()"),
    "lowercase": ("lower", "str.lower()"),
    "trimStart": ("lstrip", "str.lstrip() - JavaScript pattern"),
    "trimEnd": ("rstrip", "str.rstrip() - JavaScript pattern"),
    "charAt": ("[]", "Use indexing s[i] not s.charAt(i) - JavaScript pattern"),
    "indexOf": ("find", "str.find() or 'in' operator - JavaScript pattern"),
    "lastIndexOf": ("rfind", "str.rfind() - JavaScript pattern"),
    "substring": ("[]", "Use slicing s[start:end] - JavaScript pattern"),
    "includes": ("in", "Use 'in' operator - JavaScript pattern"),
    "repeat": ("*", "Use s * n for repetition - JavaScript pattern"),
    "padStart": ("rjust", "str.rjust() or str.zfill() - JavaScript pattern"),
    "padEnd": ("ljust", "str.ljust() - JavaScript pattern"),
    "toUpperCase": ("upper", "str.upper() - JavaScript pattern"),
    "toLowerCase": ("lower", "str.lower() - JavaScript pattern"),
    "toString": ("str", "Use str() builtin - JavaScript pattern"),
    # List/Array methods - only flag methods that don't exist in Python
    "unshift": ("insert", "list.insert(0, x) - JavaScript pattern"),
    "shift": ("pop", "list.pop(0) - JavaScript pattern"),
    "splice": ("[]", "Use slicing/del for splice - JavaScript pattern"),
    "slice": ("[]", "Use slicing list[start:end] - JavaScript pattern"),
    "concat": ("+", "Use + or extend() - JavaScript pattern"),
    "forEach": ("for", "Use for loop - JavaScript pattern"),
    "findIndex": ("next", "Use next(i for i,x in enumerate(list) if cond)"),
    "some": ("any", "Use any(cond for x in list)"),
    "every": ("all", "Use all(cond for x in list)"),
    "flat": ("itertools.chain", "Use itertools.chain.from_iterable()"),
    "flatMap": ("itertools.chain", "Use chain.from_iterable(f(x) for x in list)"),
    "length": ("len", "Use len(list) not list.length - JavaScript pattern"),
    # Dict methods
    "hasOwnProperty": ("in", "Use 'key in dict' - JavaScript pattern"),
    "keys": (None, None),  # Valid in Python
    "values": (None, None),  # Valid in Python
    "entries": ("items", "dict.items() - JavaScript pattern"),
    "assign": ("update", "dict.update() or {**d1, **d2} - JavaScript pattern"),
    "freeze": (None, "Python dicts are mutable; use types.MappingProxyType"),
    # Type checking
    "typeof": ("type", "Use type() or isinstance() - JavaScript pattern"),
    "instanceof": ("isinstance", "Use isinstance() - JavaScript pattern"),
    # Java patterns
    "equals": ("==", "Use == for equality - Java pattern"),
    "equalsIgnoreCase": ("lower", "Use s1.lower() == s2.lower() - Java pattern"),
    "compareTo": ("<>", "Use comparison operators - Java pattern"),
    "println": ("print", "Use print() - Java pattern"),
    "printf": ("print", "Use print() or f-string - Java pattern"),
    "getClass": ("type", "Use type() or __class__ - Java pattern"),
    "hashCode": ("hash", "Use hash() builtin - Java pattern"),
    "isEmpty": ("not", "Use 'not obj' or 'len(obj) == 0' - Java pattern"),
    "startsWith": ("startswith", "Use str.startswith() - Java pattern"),
    "endsWith": ("endswith", "Use str.endswith() - Java pattern"),
    "toCharArray": ("list", "Use list(s) - Java pattern"),
    "getBytes": ("encode", "Use str.encode() - Java pattern"),
    # Ruby patterns
    "each": ("for", "Use for loop - Ruby pattern"),
    "each_with_index": ("enumerate", "Use enumerate() - Ruby pattern"),
    "collect": ("list comprehension", "Use [f(x) for x in list] - Ruby pattern"),
    "select": ("list comprehension", "Use [x for x in list if cond] - Ruby pattern"),
    "reject": ("list comprehension", "Use [x for x in list if not cond] - Ruby pattern"),
    "detect": ("next", "Use next(x for x in list if cond) - Ruby pattern"),
    "inject": ("functools.reduce", "Use functools.reduce() - Ruby pattern"),
    "first": ("[0]", "Use [0] indexing - Ruby pattern"),
    "last": ("[-1]", "Use [-1] indexing - Ruby pattern"),
    "chomp": ("strip", "Use str.strip() - Ruby pattern"),
    "chop": ("[:-1]", "Use slicing s[:-1] - Ruby pattern"),
    "gsub": ("replace", "Use str.replace() or re.sub() - Ruby pattern"),
    "split": (None, None),  # Valid in Python
    "join": (None, None),  # Valid in Python
    "reverse": (None, None),  # Valid in Python (list.reverse())
    "upcase": ("upper", "Use str.upper() - Ruby pattern"),
    "downcase": ("lower", "Use str.lower() - Ruby pattern"),
    "capitalize": (None, None),  # Valid in Python
    "empty?": ("not", "Use 'not obj' or 'len(obj) == 0' - Ruby pattern"),
    "nil?": ("is None", "Use 'is None' - Ruby pattern"),
    "include?": ("in", "Use 'in' operator - Ruby pattern"),
    "present?": ("bool", "Use bool(obj) or 'if obj:' - Ruby/Rails pattern"),
    "blank?": ("not", "Use 'not obj' - Ruby/Rails pattern"),
    # Go patterns
    "Println": ("print", "Use print() - Go fmt pattern"),
    "Printf": ("print", "Use print() or f-string - Go fmt pattern"),
    "Sprintf": ("format", "Use f-string or str.format() - Go fmt pattern"),
    "Error": ("Exception", "Use raise Exception() - Go pattern"),
    "Errorf": ("Exception", "Use raise Exception(f'...') - Go pattern"),
    "make": (None, "Use [] for list, {} for dict - Go pattern"),
    "append": (None, None),  # Valid in Python (list.append)
    "len": (None, None),  # Valid in Python
    "cap": (None, "Python lists grow dynamically - Go pattern"),
    # C# patterns
    "Length": ("len", "Use len(obj) - C# pattern"),
    "Count": ("len", "Use len(obj) - C# pattern"),
    "Add": ("append", "Use list.append() - C# pattern"),
    "Remove": ("remove", "Use list.remove() - C# pattern"),
    "Contains": ("in", "Use 'in' operator - C# pattern"),
    "IndexOf": ("index", "Use list.index() or str.find() - C# pattern"),
    "ToLower": ("lower", "Use str.lower() - C# pattern"),
    "ToUpper": ("upper", "Use str.upper() - C# pattern"),
    "Trim": ("strip", "Use str.strip() - C# pattern"),
    "Split": ("split", "Use str.split() - C# pattern"),
    "Join": ("join", "Use str.join() or ''.join() - C# pattern"),
    "Replace": ("replace", "Use str.replace() - C# pattern"),
    "Substring": ("[]", "Use slicing s[start:end] - C# pattern"),
    "StartsWith": ("startswith", "Use str.startswith() - C# pattern"),
    "EndsWith": ("endswith", "Use str.endswith() - C# pattern"),
    "WriteLine": ("print", "Use print() - C# pattern"),
    "ReadLine": ("input", "Use input() - C# pattern"),
    "Parse": (None, "Use int(), float(), etc. - C# pattern"),
    "TryParse": (None, "Use try/except with int(), float() - C# pattern"),
    "ToString": ("str", "Use str() builtin - C# pattern"),
    # PHP patterns
    "var_dump": ("print", "Use print() or pprint - PHP pattern"),
    "print_r": ("print", "Use print() or pprint - PHP pattern"),
    "isset": ("is not None", "Use 'is not None' or 'in' - PHP pattern"),
    "unset": ("del", "Use del statement - PHP pattern"),
    "array_push": ("append", "Use list.append() - PHP pattern"),
    "array_pop": ("pop", "Use list.pop() - PHP pattern"),
    "array_merge": ("+", "Use + or extend() - PHP pattern"),
    "array_keys": ("keys", "Use dict.keys() - PHP pattern"),
    "array_values": ("values", "Use dict.values() - PHP pattern"),
    "strlen": ("len", "Use len() - PHP pattern"),
    "strpos": ("find", "Use str.find() - PHP pattern"),
    "str_replace": ("replace", "Use str.replace() - PHP pattern"),
    "explode": ("split", "Use str.split() - PHP pattern"),
    "implode": ("join", "Use str.join() - PHP pattern"),
    "strtolower": ("lower", "Use str.lower() - PHP pattern"),
    "strtoupper": ("upper", "Use str.upper() - PHP pattern"),
    "preg_match": ("re.search", "Use re.search() - PHP pattern"),
    "preg_replace": ("re.sub", "Use re.sub() - PHP pattern"),
    "file_get_contents": ("open", "Use open().read() - PHP pattern"),
    "file_put_contents": ("open", "Use open().write() - PHP pattern"),
    "json_encode": ("json.dumps", "Use json.dumps() - PHP pattern"),
    "json_decode": ("json.loads", "Use json.loads() - PHP pattern"),
    # Valid Python methods - explicitly mark as valid to avoid false positives
    # These exist in Python standard library or are common in popular packages
    "find": (None, None),  # str.find() is valid
    "sub": (None, None),  # re.sub() is valid
    "push": (None, None),  # Could be custom method (e.g., stack.push())
    "echo": (None, None),  # click.echo() is valid
    "trim": (None, None),  # Could be custom method
    "contains": (None, None),  # pandas/polars have .contains()
    "map": (None, None),  # map() builtin, pandas.map(), etc.
    "filter": (None, None),  # filter() builtin
    "reduce": (None, None),  # functools.reduce()
    "size": (None, None),  # numpy/pandas .size attribute
    "count": (None, None),  # str.count(), list.count()
    "substr": (None, None),  # Could be custom method
    "print": (None, None),  # Valid builtin
    "sorted": (None, None),  # Valid builtin
    "reversed": (None, None),  # Valid builtin
}


def check_hallucinated_method(method_name: str) -> str | None:
    """
    Check if a method name is a known hallucination.

    Returns error message with correction if hallucinated, None otherwise.
    """
    if method_name not in HALLUCINATED_METHODS:
        return None

    correct, hint = HALLUCINATED_METHODS[method_name]
    if correct is None:
        return None  # Method is valid

    return f"'{method_name}' is not a Python method. {hint}"
