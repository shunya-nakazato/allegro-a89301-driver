"""The ``Field`` bit-field type used by the A89301 register table."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from allegro_a89301.constants import MAX_REGISTER_ADDRESS, REGISTER_DATA_BITS, WORD_MASK
from allegro_a89301.errors import ValueRangeError


@dataclass(frozen=True)
class Field:
    """A bit field [msb:lsb] within a 16-bit register.

    The field's name lives in the ``REGISTERS`` table key, not here.
    ``conversion`` maps a raw value to a physical quantity and ``inverse`` maps
    it back (``None`` = the field is used raw). ``value_type`` is the Python
    type a read yields (``int`` or ``float``).
    """

    register: int
    msb: int
    lsb: int
    conversion: Callable[[int], int | float] | None = None
    value_type: type[int | float] = int
    inverse: Callable[[int | float], float] | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.lsb <= self.msb <= REGISTER_DATA_BITS - 1:
            raise ValueError(
                f"invalid bit range [{self.msb}:{self.lsb}] "
                f"(must satisfy 0 <= lsb <= msb <= {REGISTER_DATA_BITS - 1})"
            )
        if not 0 <= self.register <= MAX_REGISTER_ADDRESS:
            raise ValueError(f"register {self.register} out of range 0..{MAX_REGISTER_ADDRESS}")

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

    def insert(self, word: int, value: int) -> int:
        """Return ``word`` with only this field's bits replaced by raw ``value``.

        Raises ValueRangeError for a non-int or out-of-range ``value``.
        """
        _check_word(word)
        value = self._check_raw(value)
        return (word & ~self.mask) | (value << self.lsb)

    def encode(self, value: int | float) -> int:
        """Convert a physical (or raw, when no ``inverse``) value to a raw value.

        The inverse conversion result is rounded to the nearest raw step.
        Raises ValueRangeError for a non-int raw value or when the result does
        not fit the field width.
        """
        raw = round(self.inverse(value)) if self.inverse is not None else value
        return self._check_raw(raw)

    def decode(self, word: int) -> int | float:
        """Decode a raw 16-bit ``word`` into this field's typed value.

        Extracts this field's bits, applies the physical ``conversion`` (raw when
        absent), then coerces the result to ``value_type`` so the returned value's
        type is guaranteed regardless of the conversion's own arithmetic.
        """
        raw = self.extract(word)
        value = self.conversion(raw) if self.conversion is not None else raw
        return self.value_type(value)

    def _check_raw(self, raw: object) -> int:
        # Non-int is a value error too, so every input failure stays inside
        # the A89301Error hierarchy.
        if not isinstance(raw, int):
            raise ValueRangeError(f"raw value must be int, got {type(raw).__name__}")
        if not 0 <= raw <= self.max_value:
            raise ValueRangeError(f"raw value {raw} out of range 0..{self.max_value}")
        return raw


def _check_word(word: int) -> None:
    if not 0 <= word <= WORD_MASK:
        raise ValueRangeError(f"word {word} out of range 0..0x{WORD_MASK:04X}")
