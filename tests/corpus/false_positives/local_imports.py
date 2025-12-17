"""Module with local imports.

This file tests that local imports are not flagged as hallucinations.
The imports below reference other files in the same directory.
"""

# These should NOT be flagged as hallucinated imports
# when helper_module.py exists in the same directory
import config
from helper_module import helper_function
from utils import utility_function


def main() -> None:
    """Use the local imports."""
    helper_function()
    utility_function()
    print(config.VALUE)
