"""Tests for dead code detection."""

import pytest
from pathlib import Path

from sloppy.detector import Detector


def test_unused_function_detected(tmp_python_file):
    """Test that unused functions are detected."""
    code = '''
def used_func():
    return 42

def unused_func():
    return "never called"

result = used_func()
'''
    file = tmp_python_file(code)
    detector = Detector()
    issues = detector.scan([file])
    
    dead = [i for i in issues if i.pattern_id == "dead_code"]
    assert len(dead) == 1
    assert "unused_func" in dead[0].message


def test_used_function_not_flagged(tmp_python_file):
    """Test that used functions are not flagged."""
    code = '''
def helper():
    return 42

def main():
    return helper() * 2

result = main()
'''
    file = tmp_python_file(code)
    detector = Detector()
    issues = detector.scan([file])
    
    dead = [i for i in issues if i.pattern_id == "dead_code"]
    assert len(dead) == 0


def test_unused_class_detected(tmp_python_file):
    """Test that unused classes are detected."""
    code = '''
class UsedClass:
    pass

class UnusedClass:
    pass

obj = UsedClass()
'''
    file = tmp_python_file(code)
    detector = Detector()
    issues = detector.scan([file])
    
    dead = [i for i in issues if i.pattern_id == "dead_code"]
    assert len(dead) == 1
    assert "UnusedClass" in dead[0].message


def test_class_as_base_counts_as_usage(tmp_python_file):
    """Test that classes used as base classes are not flagged."""
    code = '''
class BaseClass:
    pass

class ChildClass(BaseClass):
    pass

obj = ChildClass()
'''
    file = tmp_python_file(code)
    detector = Detector()
    issues = detector.scan([file])
    
    dead = [i for i in issues if i.pattern_id == "dead_code"]
    assert len(dead) == 0


def test_decorated_function_not_flagged(tmp_python_file):
    """Test that decorated functions are not flagged."""
    code = '''
from functools import lru_cache

@lru_cache
def cached_func(x):
    return x * 2
'''
    file = tmp_python_file(code)
    detector = Detector()
    issues = detector.scan([file])
    
    dead = [i for i in issues if i.pattern_id == "dead_code"]
    # lru_cache decorated functions might be called externally
    assert len(dead) == 0


def test_test_functions_not_flagged(tmp_python_file):
    """Test that test functions are not flagged."""
    code = '''
def test_something():
    assert True

def test_another_thing():
    assert 1 + 1 == 2
'''
    file = tmp_python_file(code)
    detector = Detector()
    issues = detector.scan([file])
    
    dead = [i for i in issues if i.pattern_id == "dead_code"]
    assert len(dead) == 0


def test_main_function_not_flagged(tmp_python_file):
    """Test that main functions are not flagged."""
    code = '''
def main():
    print("Hello")

if __name__ == "__main__":
    main()
'''
    file = tmp_python_file(code)
    detector = Detector()
    issues = detector.scan([file])
    
    dead = [i for i in issues if i.pattern_id == "dead_code"]
    assert len(dead) == 0


def test_dunder_methods_not_flagged(tmp_python_file):
    """Test that dunder methods are not flagged."""
    code = '''
class MyClass:
    def __init__(self):
        self.value = 42
    
    def __str__(self):
        return str(self.value)
    
    def __repr__(self):
        return f"MyClass({self.value})"

obj = MyClass()
'''
    file = tmp_python_file(code)
    detector = Detector()
    issues = detector.scan([file])
    
    dead = [i for i in issues if i.pattern_id == "dead_code"]
    assert len(dead) == 0


def test_method_called_on_instance_not_flagged(tmp_python_file):
    """Test that methods called on instances are not flagged."""
    code = '''
class Calculator:
    def add(self, a, b):
        return a + b
    
    def subtract(self, a, b):
        return a - b

calc = Calculator()
result = calc.add(1, 2)
'''
    file = tmp_python_file(code)
    detector = Detector()
    issues = detector.scan([file])
    
    dead = [i for i in issues if i.pattern_id == "dead_code"]
    # subtract is not called but class is used, so we don't flag it
    assert len(dead) == 0


def test_disabled_pattern(tmp_python_file):
    """Test that dead_code can be disabled."""
    code = '''
def unused_func():
    return 42
'''
    file = tmp_python_file(code)
    detector = Detector(disabled_patterns=["dead_code"])
    issues = detector.scan([file])
    
    dead = [i for i in issues if i.pattern_id == "dead_code"]
    assert len(dead) == 0
