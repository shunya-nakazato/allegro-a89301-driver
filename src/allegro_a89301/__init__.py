"""I2C driver for the Allegro A89301 motor controller.

``A89301Driver`` is the primary interface: it owns the I2C connection and reads
and writes fields by name, driven by the field table in ``allegro_a89301.registers``.
``AsyncA89301Driver`` is its asyncio counterpart with the same contract.
"""

from allegro_a89301.async_driver import AsyncA89301Driver
from allegro_a89301.constants import SLAVE_ADDRESS
from allegro_a89301.driver import A89301Driver
from allegro_a89301.errors import (
    A89301Error,
    NotWritableError,
    UnknownFieldError,
    ValueRangeError,
)

__all__ = [
    "SLAVE_ADDRESS",
    "A89301Driver",
    "AsyncA89301Driver",
    "A89301Error",
    "UnknownFieldError",
    "NotWritableError",
    "ValueRangeError",
]
