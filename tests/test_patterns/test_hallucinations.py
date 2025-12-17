"""Tests for hallucination detection patterns."""

from sloppy.detector import Detector


def test_pass_placeholder_detected(tmp_python_file):
    """Test that pass placeholders are detected."""
    code = """
def placeholder_func():
    pass
"""
    file = tmp_python_file(code)
    detector = Detector()
    issues = detector.scan([file])

    pass_issues = [i for i in issues if i.pattern_id == "pass_placeholder"]
    assert len(pass_issues) == 1


def test_ellipsis_placeholder_detected(tmp_python_file):
    """Test that ellipsis placeholders are detected."""
    code = """
def placeholder_func():
    ...
"""
    file = tmp_python_file(code)
    detector = Detector()
    issues = detector.scan([file])

    ellipsis_issues = [i for i in issues if i.pattern_id == "ellipsis_placeholder"]
    assert len(ellipsis_issues) == 1


def test_notimplemented_placeholder_detected(tmp_python_file):
    """Test that NotImplementedError placeholders are detected."""
    code = """
def placeholder_func():
    raise NotImplementedError()
"""
    file = tmp_python_file(code)
    detector = Detector()
    issues = detector.scan([file])

    not_impl_issues = [i for i in issues if i.pattern_id == "notimplemented_placeholder"]
    assert len(not_impl_issues) == 1


def test_real_implementation_not_flagged(tmp_python_file):
    """Test that real implementations are not flagged as placeholders."""
    code = """
def real_func(x):
    result = x * 2
    return result
"""
    file = tmp_python_file(code)
    detector = Detector()
    issues = detector.scan([file])

    placeholder_ids = {"pass_placeholder", "ellipsis_placeholder", "notimplemented_placeholder"}
    placeholder_issues = [i for i in issues if i.pattern_id in placeholder_ids]
    assert len(placeholder_issues) == 0


def test_hallucinated_import_wrong_module(tmp_python_file):
    """Test that imports from wrong modules are detected."""
    code = """
from requests import JSONResponse
"""
    file = tmp_python_file(code)
    detector = Detector()
    issues = detector.scan([file])

    hallucinated = [i for i in issues if i.pattern_id == "hallucinated_import"]
    assert len(hallucinated) == 1
    assert "starlette" in hallucinated[0].message or "fastapi" in hallucinated[0].message


def test_hallucinated_import_dataclass_wrong_module(tmp_python_file):
    """Test that dataclass imported from wrong module is detected."""
    code = """
from collections import dataclass
"""
    file = tmp_python_file(code)
    detector = Detector()
    issues = detector.scan([file])

    hallucinated = [i for i in issues if i.pattern_id == "hallucinated_import"]
    assert len(hallucinated) == 1
    assert "dataclasses" in hallucinated[0].message


def test_valid_import_not_flagged(tmp_python_file):
    """Test that valid imports are not flagged."""
    code = """
from dataclasses import dataclass
from typing import Optional
import json
"""
    file = tmp_python_file(code)
    detector = Detector()
    issues = detector.scan([file])

    hallucinated = [
        i for i in issues if i.pattern_id in ("hallucinated_import", "wrong_stdlib_import")
    ]
    assert len(hallucinated) == 0


def test_javascript_pattern_detected(tmp_python_file):
    """Test that JavaScript patterns (json.parse) are detected."""
    code = """
from json import parse
"""
    file = tmp_python_file(code)
    detector = Detector()
    issues = detector.scan([file])

    hallucinated = [i for i in issues if i.pattern_id == "hallucinated_import"]
    assert len(hallucinated) == 1
    assert "json.loads" in hallucinated[0].message


def test_hallucinated_method_unshift(tmp_python_file):
    """Test that JavaScript .unshift() method is detected."""
    code = """
items = []
items.unshift(1)
"""
    file = tmp_python_file(code)
    detector = Detector()
    issues = detector.scan([file])

    method_issues = [i for i in issues if i.pattern_id == "hallucinated_method"]
    assert len(method_issues) == 1
    assert "insert" in method_issues[0].message


def test_push_not_flagged(tmp_python_file):
    """Test that .push() is NOT flagged - it could be a valid custom method."""
    code = """
# push() is valid in many contexts:
# - Stack.push(), Queue.push()
# - click: push_module.push()
items = []
items.push(1)
"""
    file = tmp_python_file(code)
    detector = Detector()
    issues = detector.scan([file])

    # push should NOT be flagged as it could be a custom method
    method_issues = [i for i in issues if i.pattern_id == "hallucinated_method"]
    assert len(method_issues) == 0


def test_hallucinated_method_foreach(tmp_python_file):
    """Test that JavaScript .forEach() is detected."""
    code = """
items = [1, 2, 3]
items.forEach(lambda x: print(x))
"""
    file = tmp_python_file(code)
    detector = Detector()
    issues = detector.scan([file])

    method_issues = [i for i in issues if i.pattern_id == "hallucinated_method"]
    assert len(method_issues) == 1
    assert "for loop" in method_issues[0].message


def test_hallucinated_attribute_length(tmp_python_file):
    """Test that .length attribute is detected."""
    code = """
items = [1, 2, 3]
n = items.length
"""
    file = tmp_python_file(code)
    detector = Detector()
    issues = detector.scan([file])

    attr_issues = [i for i in issues if i.pattern_id == "hallucinated_attribute"]
    assert len(attr_issues) == 1
    assert "len(obj)" in attr_issues[0].message


def test_valid_method_not_flagged(tmp_python_file):
    """Test that valid Python methods are not flagged."""
    code = """
items = []
items.append(1)
items.extend([2, 3])
s = "hello"
s.upper()
s.strip()
"""
    file = tmp_python_file(code)
    detector = Detector()
    issues = detector.scan([file])

    hallucinated = [
        i for i in issues if i.pattern_id in ("hallucinated_method", "hallucinated_attribute")
    ]
    assert len(hallucinated) == 0


def test_java_equals_detected(tmp_python_file):
    """Test that Java .equals() method is detected."""
    code = """
s1 = "hello"
s2 = "world"
result = s1.equals(s2)
"""
    file = tmp_python_file(code)
    detector = Detector()
    issues = detector.scan([file])

    method_issues = [i for i in issues if i.pattern_id == "hallucinated_method"]
    assert len(method_issues) == 1
    assert "Java" in method_issues[0].message


def test_ruby_each_detected(tmp_python_file):
    """Test that Ruby .each method is detected."""
    code = """
items = [1, 2, 3]
items.each(lambda x: print(x))
"""
    file = tmp_python_file(code)
    detector = Detector()
    issues = detector.scan([file])

    method_issues = [i for i in issues if i.pattern_id == "hallucinated_method"]
    assert len(method_issues) == 1
    assert "Ruby" in method_issues[0].message


def test_csharp_length_attribute_detected(tmp_python_file):
    """Test that C# .Length attribute is detected."""
    code = """
items = [1, 2, 3]
n = items.Length
"""
    file = tmp_python_file(code)
    detector = Detector()
    issues = detector.scan([file])

    attr_issues = [i for i in issues if i.pattern_id == "hallucinated_attribute"]
    assert len(attr_issues) == 1
    assert "C#" in attr_issues[0].message


def test_php_strlen_detected(tmp_python_file):
    """Test that PHP strlen() is detected."""
    code = """
s = "hello"
n = s.strlen()
"""
    file = tmp_python_file(code)
    detector = Detector()
    issues = detector.scan([file])

    method_issues = [i for i in issues if i.pattern_id == "hallucinated_method"]
    assert len(method_issues) == 1
    assert "PHP" in method_issues[0].message


def test_go_println_detected(tmp_python_file):
    """Test that Go fmt.Println pattern is detected."""
    code = """
fmt.Println("hello")
"""
    file = tmp_python_file(code)
    detector = Detector()
    issues = detector.scan([file])

    method_issues = [i for i in issues if i.pattern_id == "hallucinated_method"]
    assert len(method_issues) == 1
    assert "Go" in method_issues[0].message
