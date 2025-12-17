"""Content inside multi-line strings should NOT be flagged.

This is a test file for the multiline_string_lines fix.
The following should NOT trigger any warnings:

    magic_number = 42
    print('hello')
    if x else y if z else w
"""


def docstring_with_patterns():
    """
    This docstring contains patterns that SHOULD NOT be flagged:

    Example with magic numbers:
        timeout = 3600  # one hour in seconds
        retries = 5

    Example with print (not debug_print):
        print('Hello, world!')

    Example with nested ternary (just documentation):
        result = x if a else y if b else z
    """
    return True


MULTILINE_CONSTANT = """
This multi-line string constant also has patterns:
    count = 42
    print(result)
    if this else that if foo else bar
Should all be ignored.
"""


class ExampleClass:
    """
    Class docstring with code examples.

    Usage:
        >>> obj = ExampleClass()
        >>> obj.process(timeout=30)
        >>> print(obj.result)
    """

    def method_with_docstring(self):
        """
        Method with patterns in docstring.

        The number 42 appears here.
        Also print('something') appears.
        """
        pass
