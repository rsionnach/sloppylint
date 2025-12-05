"""Tests for cross-file duplicate detection."""

import pytest
from pathlib import Path
import tempfile
import os

from sloppy.detector import Detector


@pytest.fixture
def tmp_dir():
    """Create a temporary directory with Python files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_duplicate_function_detected(tmp_dir):
    """Test that duplicate functions across files are detected."""
    # Create two files with the same function
    file1 = tmp_dir / "module1.py"
    file2 = tmp_dir / "module2.py"
    
    code = '''
def process_data(items):
    result = []
    for item in items:
        if item > 0:
            result.append(item * 2)
    return result
'''
    
    file1.write_text(code)
    file2.write_text(code)
    
    detector = Detector()
    issues = detector.scan([tmp_dir])
    
    duplicates = [i for i in issues if i.pattern_id == "duplicate_code"]
    assert len(duplicates) == 1
    assert "process_data" in duplicates[0].message


def test_different_functions_not_flagged(tmp_dir):
    """Test that different functions are not flagged as duplicates."""
    file1 = tmp_dir / "module1.py"
    file2 = tmp_dir / "module2.py"
    
    code1 = '''
def func1(items):
    result = []
    for item in items:
        result.append(item * 2)
    return result
'''
    
    code2 = '''
def func2(items):
    total = 0
    for item in items:
        total += item
    return total
'''
    
    file1.write_text(code1)
    file2.write_text(code2)
    
    detector = Detector()
    issues = detector.scan([tmp_dir])
    
    duplicates = [i for i in issues if i.pattern_id == "duplicate_code"]
    assert len(duplicates) == 0


def test_duplicate_class_detected(tmp_dir):
    """Test that duplicate classes across files are detected."""
    file1 = tmp_dir / "models1.py"
    file2 = tmp_dir / "models2.py"
    
    code = '''
class DataProcessor:
    def __init__(self, data):
        self.data = data
    
    def process(self):
        return [x * 2 for x in self.data]
    
    def validate(self):
        return all(x > 0 for x in self.data)
'''
    
    file1.write_text(code)
    file2.write_text(code)
    
    detector = Detector()
    issues = detector.scan([tmp_dir])
    
    duplicates = [i for i in issues if i.pattern_id == "duplicate_code"]
    assert len(duplicates) >= 1


def test_small_functions_not_flagged(tmp_dir):
    """Test that small functions (< 5 lines) are not flagged."""
    file1 = tmp_dir / "utils1.py"
    file2 = tmp_dir / "utils2.py"
    
    code = '''
def add(a, b):
    return a + b
'''
    
    file1.write_text(code)
    file2.write_text(code)
    
    detector = Detector()
    issues = detector.scan([tmp_dir])
    
    duplicates = [i for i in issues if i.pattern_id == "duplicate_code"]
    assert len(duplicates) == 0


def test_test_functions_not_flagged(tmp_dir):
    """Test that test functions are not flagged as duplicates."""
    file1 = tmp_dir / "test_module1.py"
    file2 = tmp_dir / "test_module2.py"
    
    code = '''
def test_something():
    items = [1, 2, 3]
    result = sum(items)
    assert result == 6
    assert len(items) == 3
'''
    
    file1.write_text(code)
    file2.write_text(code)
    
    detector = Detector()
    issues = detector.scan([tmp_dir])
    
    duplicates = [i for i in issues if i.pattern_id == "duplicate_code"]
    assert len(duplicates) == 0


def test_disabled_pattern(tmp_dir):
    """Test that duplicate_code can be disabled."""
    file1 = tmp_dir / "module1.py"
    file2 = tmp_dir / "module2.py"
    
    code = '''
def process_data(items):
    result = []
    for item in items:
        if item > 0:
            result.append(item * 2)
    return result
'''
    
    file1.write_text(code)
    file2.write_text(code)
    
    detector = Detector(disabled_patterns=["duplicate_code"])
    issues = detector.scan([tmp_dir])
    
    duplicates = [i for i in issues if i.pattern_id == "duplicate_code"]
    assert len(duplicates) == 0


def test_single_file_no_duplicates(tmp_dir):
    """Test that duplicates within same file are not flagged."""
    file1 = tmp_dir / "module.py"
    
    code = '''
def func1(items):
    result = []
    for item in items:
        result.append(item * 2)
    return result

def func2(items):
    result = []
    for item in items:
        result.append(item * 2)
    return result
'''
    
    file1.write_text(code)
    
    detector = Detector()
    issues = detector.scan([tmp_dir])
    
    # Same-file duplicates are not flagged by cross-file detector
    duplicates = [i for i in issues if i.pattern_id == "duplicate_code"]
    assert len(duplicates) == 0
