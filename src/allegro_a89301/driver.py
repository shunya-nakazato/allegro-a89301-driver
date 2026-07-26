"""Synchronous A89301 driver that owns a real I2C connection (smbus2)."""

from __future__ import annotations

from smbus2 import SMBus, i2c_msg

from allegro_a89301.constants import READ_LENGTH, SLAVE_ADDRESS
from allegro_a89301.field import Reading
from allegro_a89301.table import REGISTERS

__all__ = ["I2CDriver"]


class I2CDriver:
    """Reads A89301 fields by name over a real I2C bus (smbus2).

    Owns the bus for its lifetime; call :meth:`close` or use it as a context
    manager to release the underlying ``/dev/i2c-N`` handle.
    """

    def __init__(self, bus: int = 1) -> None:
        self._bus = self._open_bus(bus)

    def _open_bus(self, bus: int) -> SMBus:
        """Open and return the I2C bus (owned by this driver)."""
        return SMBus(bus)

    def close(self) -> None:
        """Release the owned I2C bus."""
        self._bus.close()

    def __enter__(self) -> I2CDriver:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def read(self, name: str) -> Reading:
        """Read ``name`` synchronously and return a typed :class:`Reading`.

        The field decodes its own bits, conversion, and type (see
        :meth:`Field.decode`). Raises KeyError if ``name`` is not a defined field.

        Uses two transactions with a STOP between them (datasheet), not a
        repeated-start block read.
        """
        try:
            field = REGISTERS[name]
        except KeyError:
            raise KeyError(f"{name!r} is not a defined A89301 field") from None
        write_msg = i2c_msg.write(SLAVE_ADDRESS, [field.register])
        read_msg = i2c_msg.read(SLAVE_ADDRESS, READ_LENGTH)
        self._bus.i2c_rdwr(write_msg)  # transaction 1, then STOP
        self._bus.i2c_rdwr(read_msg)  # transaction 2
        high, low = list(read_msg)
        return field.decode((high << 8) | low)
