"""Valid Python methods that should NOT be flagged as hallucinations.

These are all legitimate Python methods that exist in the standard library
or common packages.
"""

import re
from functools import reduce


def test_string_find() -> None:
    """str.find() is a valid Python method."""
    text = "hello world"
    pos = text.find("world")
    assert pos == 6


def test_regex_sub() -> None:
    """re.sub() is a valid Python method."""
    result = re.sub(r"\d+", "X", "abc123def")
    assert result == "abcXdef"


def test_builtin_map_filter_reduce() -> None:
    """map(), filter(), reduce() are valid Python builtins."""
    numbers = [1, 2, 3, 4, 5]

    # map is valid
    doubled = [x * 2 for x in numbers]

    # filter is valid
    evens = list(filter(lambda x: x % 2 == 0, numbers))

    # reduce is valid (from functools)
    total = reduce(lambda a, b: a + b, numbers)

    assert doubled == [2, 4, 6, 8, 10]
    assert evens == [2, 4]
    assert total == 15


def test_string_count() -> None:
    """str.count() is a valid Python method."""
    text = "banana"
    count = text.count("a")
    assert count == 3


class Stack:
    """Example class with push method."""

    def __init__(self) -> None:
        self._items: list = []

    def push(self, item: object) -> None:
        """push() is valid as a custom method."""
        self._items.append(item)

    def pop(self) -> object:
        """pop() is valid."""
        return self._items.pop()
