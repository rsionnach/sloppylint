"""Tests for structural pattern detection - AI-specific patterns."""

from sloppy.detector import Detector


def test_single_method_class_detected(tmp_python_file):
    """Test that single-method classes are detected."""
    code = """
class Processor:
    def __init__(self, data):
        self.data = data

    def process(self):
        return self.data.strip()
"""
    file = tmp_python_file(code)
    detector = Detector()
    issues = detector.scan([file])

    single_method_issues = [i for i in issues if i.pattern_id == "single_method_class"]
    assert len(single_method_issues) == 1


def test_multi_method_class_not_flagged(tmp_python_file):
    """Test that multi-method classes are not flagged."""
    code = """
class Processor:
    def __init__(self, data):
        self.data = data

    def process(self):
        return self.data.strip()

    def validate(self):
        return bool(self.data)
"""
    file = tmp_python_file(code)
    detector = Detector()
    issues = detector.scan([file])

    single_method_issues = [i for i in issues if i.pattern_id == "single_method_class"]
    assert len(single_method_issues) == 0
