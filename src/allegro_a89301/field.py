"""The ``Field`` bit-field type used by the A89301 register table."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from allegro_a89301.constants import MAX_REGISTER_ADDRESS, REGISTER_DATA_BITS, WORD_MASK


@dataclass(frozen=True)
class Reading:
    """A decoded register read: the field ``name`` and its typed ``value``."""

    name: str
    value: int | float


@dataclass(frozen=True)
class Field:
    """A named bit field [msb:lsb] within a 16-bit register.

    ``conversion`` maps a raw value to a physical quantity (``None`` = read as raw).
    ``value_type`` is the Python type a read yields (``int`` or ``float``).
    """

    name: str
    register: int
    msb: int
    lsb: int
    description: str = ""
    conversion: Callable[[int], int | float] | None = None
    value_type: type[int | float] = int

    def __post_init__(self) -> None:
        if not 0 <= self.lsb <= self.msb <= REGISTER_DATA_BITS - 1:
            raise ValueError(
                f"{self.name}: invalid bit range [{self.msb}:{self.lsb}] "
                f"(must satisfy 0 <= lsb <= msb <= {REGISTER_DATA_BITS - 1})"
            )
        if not 0 <= self.register <= MAX_REGISTER_ADDRESS:
            raise ValueError(
                f"{self.name}: register {self.register} out of range 0..{MAX_REGISTER_ADDRESS}"
            )

    @property
    def width(self) -> int:
        return self.msb - self.lsb + 1

    @property
    def max_value(self) -> int:
        return (1 << self.width) - 1

    @property
    def mask(self) -> int:
        return self.max_value << self.lsb

    def extract(self, word: int) -> int:
        _check_word(word)
        return (word & self.mask) >> self.lsb

    def decode(self, word: int) -> Reading:
        """Decode a raw 16-bit ``word`` into a typed :class:`Reading`.

        Extracts this field's bits, applies the physical ``conversion`` (raw when
        absent), then coerces the result to ``value_type`` so the returned value's
        type is guaranteed regardless of the conversion's own arithmetic.
        """
        raw = self.extract(word)
        value = self.conversion(raw) if self.conversion is not None else raw
        return Reading(self.name, self.value_type(value))


def _check_word(word: int) -> None:
    if not 0 <= word <= WORD_MASK:
        raise ValueError(f"word {word} out of range 0..0x{WORD_MASK:04X}")
