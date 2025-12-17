"""Abstract methods with pass/NotImplementedError.

These should NOT be flagged as placeholders because they are
legitimate abstract method definitions.
"""

from abc import ABC, abstractmethod
from typing import Protocol


class AbstractBase(ABC):
    """Abstract base class."""

    @abstractmethod
    def must_implement(self) -> str:
        """Subclasses must implement this."""
        pass

    @abstractmethod
    def also_required(self) -> int:
        """Another required method."""
        raise NotImplementedError

    @abstractmethod
    def with_docstring(self) -> None:
        """Method with docstring and ellipsis."""
        ...


class MyProtocol(Protocol):
    """Protocol definition."""

    def protocol_method(self) -> str:
        """Protocol methods use ... or pass."""
        ...

    def another_protocol_method(self) -> int:
        """Another protocol method."""
        pass
