"""The ``Field`` bit-field type used by the A89301 register table.

Vocabulary used across the library:

- ``register_bits``: the full 16-bit content of one register, with every
  field packed in place.
- ``raw_value``: one field's bits extracted as an unscaled integer, in
  register units.
- ``physical_value``: the converted quantity (Hz, V, %, ...); equal to the
  raw_value for fields without a conversion.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from allegro_a89301.constants import (
    MAX_REGISTER_ADDRESS,
    REGISTER_BITS_MASK,
    REGISTER_WIDTH,
)
from allegro_a89301.errors import ValueRangeError


@dataclass(frozen=True)
class Field:
    """A bit field [msb:lsb] within a 16-bit register.

    The field's name lives in the ``REGISTERS`` table key, not here.
    ``raw_to_physical`` converts a raw_value to a physical_value and
    ``physical_to_raw`` converts it back (``None`` = the field is used raw).
    ``physical_type`` is the Python type a read yields (``int`` or ``float``).
    """

    register: int
    msb: int
    lsb: int
    raw_to_physical: Callable[[int], int | float] | None = None
    physical_type: type[int | float] = int
    physical_to_raw: Callable[[int | float], float] | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.lsb <= self.msb <= REGISTER_WIDTH - 1:
            raise ValueError(
                f"invalid bit range [{self.msb}:{self.lsb}] "
                f"(must satisfy 0 <= lsb <= msb <= {REGISTER_WIDTH - 1})"
            )
        if not 0 <= self.register <= MAX_REGISTER_ADDRESS:
            raise ValueError(f"register {self.register} out of range 0..{MAX_REGISTER_ADDRESS}")

    @property
    def width(self) -> int:
        return self.msb - self.lsb + 1

    @property
    def max_raw_value(self) -> int:
        return (1 << self.width) - 1

    @property
    def mask(self) -> int:
        return self.max_raw_value << self.lsb

    def extract(self, register_bits: int) -> int:
        _check_register_bits(register_bits)
        return (register_bits & self.mask) >> self.lsb

    def insert(self, register_bits: int, raw_value: int) -> int:
        """Return ``register_bits`` with only this field's bits replaced by ``raw_value``.

        Raises ValueRangeError for a non-int or out-of-range ``raw_value``.
        """
        _check_register_bits(register_bits)
        raw_value = self._check_raw_value(raw_value)
        return (register_bits & ~self.mask) | (raw_value << self.lsb)

    def encode(self, physical_value: int | float) -> int:
        """Convert a physical (or raw, when no ``physical_to_raw``) value to a raw_value.

        The inverse conversion result is rounded to the nearest raw step.
        Raises ValueRangeError for a non-int raw_value or when the result does
        not fit the field width.
        """
        if self.physical_to_raw is not None:
            raw_value = round(self.physical_to_raw(physical_value))
        else:
            raw_value = physical_value
        return self._check_raw_value(raw_value)

    def decode(self, register_bits: int) -> int | float:
        """Decode 16-bit ``register_bits`` into this field's typed physical_value.

        Extracts this field's bits, applies ``raw_to_physical`` (raw when
        absent), then coerces the result to ``physical_type`` so the returned
        value's type is guaranteed regardless of the conversion's own
        arithmetic.
        """
        raw_value = self.extract(register_bits)
        if self.raw_to_physical is not None:
            physical_value = self.raw_to_physical(raw_value)
        else:
            physical_value = raw_value
        return self.physical_type(physical_value)

    def _check_raw_value(self, raw_value: object) -> int:
        # Non-int is a value error too, so every input failure stays inside
        # the A89301Error hierarchy.
        if not isinstance(raw_value, int):
            raise ValueRangeError(f"raw value must be int, got {type(raw_value).__name__}")
        if not 0 <= raw_value <= self.max_raw_value:
            raise ValueRangeError(f"raw value {raw_value} out of range 0..{self.max_raw_value}")
        return raw_value


def _check_register_bits(register_bits: int) -> None:
    if not 0 <= register_bits <= REGISTER_BITS_MASK:
        raise ValueRangeError(
            f"register bits {register_bits} out of range 0..0x{REGISTER_BITS_MASK:04X}"
        )
