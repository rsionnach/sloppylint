"""Test suite for false positive and true positive corpus.

This test suite validates that:
1. False positive files do NOT trigger unexpected warnings
2. True positive files DO trigger expected warnings

Note: sloppylint focuses ONLY on AI-specific patterns. Traditional linting
patterns (debug prints, magic numbers, exception handling) are delegated
to tools like ruff, flake8, and pylint.
"""

from pathlib import Path

from sloppy.detector import Detector

CORPUS_DIR = Path(__file__).parent


class TestFalsePositives:
    """Tests that validate we don't flag valid code."""

    def test_abstract_methods_no_placeholder_warning(self) -> None:
        """Abstract methods should not trigger placeholder warnings."""
        file = CORPUS_DIR / "false_positives" / "abstract_methods.py"
        detector = Detector()
        issues = detector.scan([file])

        placeholders = [
            i
            for i in issues
            if i.pattern_id
            in ("pass_placeholder", "ellipsis_placeholder", "notimplemented_placeholder")
        ]
        assert len(placeholders) == 0, f"Unexpected placeholder warnings: {placeholders}"

    def test_valid_python_methods_no_hallucination_warning(self) -> None:
        """Valid Python methods should not trigger hallucinated_method."""
        file = CORPUS_DIR / "false_positives" / "valid_python_methods.py"
        detector = Detector()
        issues = detector.scan([file])

        hallucinated = [i for i in issues if i.pattern_id == "hallucinated_method"]
        assert len(hallucinated) == 0, f"Unexpected hallucinated_method warnings: {hallucinated}"


class TestTruePositives:
    """Tests that validate we DO flag problematic code."""

    def test_js_patterns_flagged(self) -> None:
        """JavaScript patterns should be flagged."""
        file = CORPUS_DIR / "true_positives" / "js_patterns.py"
        detector = Detector()
        issues = detector.scan([file])

        # Should flag forEach, unshift, length, toUpperCase, etc.
        hallucinated = [
            i for i in issues if i.pattern_id in ("hallucinated_method", "hallucinated_attribute")
        ]
        assert len(hallucinated) >= 3, f"Expected JS patterns to be flagged, got: {hallucinated}"

    def test_hallucinated_imports_flagged(self) -> None:
        """Hallucinated imports should be flagged."""
        file = CORPUS_DIR / "true_positives" / "hallucinated_imports.py"
        detector = Detector()
        issues = detector.scan([file])

        hallucinated = [i for i in issues if i.pattern_id == "hallucinated_import"]
        assert len(hallucinated) >= 2, f"Expected hallucinated imports, got: {hallucinated}"

    def test_placeholder_functions_flagged(self) -> None:
        """Placeholder functions should be flagged."""
        file = CORPUS_DIR / "true_positives" / "placeholder_functions.py"
        detector = Detector()
        issues = detector.scan([file])

        placeholders = [
            i
            for i in issues
            if i.pattern_id
            in ("pass_placeholder", "ellipsis_placeholder", "notimplemented_placeholder")
        ]
        assert len(placeholders) >= 3, f"Expected placeholder warnings, got: {placeholders}"

    def test_java_patterns_flagged(self) -> None:
        """Java patterns should be flagged."""
        file = CORPUS_DIR / "true_positives" / "java_patterns.py"
        detector = Detector()
        issues = detector.scan([file])

        hallucinated = [i for i in issues if i.pattern_id == "hallucinated_method"]
        assert len(hallucinated) >= 2, f"Expected Java patterns to be flagged, got: {hallucinated}"
