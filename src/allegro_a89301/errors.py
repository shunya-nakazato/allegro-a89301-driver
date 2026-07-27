"""Exception hierarchy for the A89301 library.

Each class also subclasses the builtin (KeyError / ValueError) it historically
raised, so ``except KeyError`` / ``except ValueError`` callers keep working.
"""

from __future__ import annotations

__all__ = [
    "A89301Error",
    "UnknownFieldError",
    "NotWritableError",
    "ValueRangeError",
]


class A89301Error(Exception):
    """Base class for all A89301 library errors."""


class UnknownFieldError(A89301Error, KeyError):
    """The field name is not in the register table."""


class NotWritableError(A89301Error, ValueError):
    """The field's register is read-only, factory-controlled, or EEPROM control."""


class ValueRangeError(A89301Error, ValueError):
    """The value does not fit the field (width or physical range)."""
