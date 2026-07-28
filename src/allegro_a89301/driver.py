"""Synchronous A89301 driver that owns a real I2C connection (smbus2)."""

from __future__ import annotations

import logging
import threading
import time

from smbus2 import SMBus, i2c_msg

from allegro_a89301.constants import (
    EEPROM_ERASE_DELAY_S,
    EEPROM_WRITE_DELAY_S,
    READ_LENGTH,
    REGISTER_EEPROM_OFFSET,
    SLAVE_ADDRESS,
)
from allegro_a89301.errors import A89301Error, NotWritableError, UnknownFieldError
from allegro_a89301.field import Field
from allegro_a89301.registers import REGISTERS, WRITABLE_REGISTERS

__all__ = ["A89301Driver"]

logger = logging.getLogger(__name__)


def _encode_write_frame(register: int, register_bits: int) -> list[int]:
    """Datasheet write frame after the slave address: [register, D[15:8], D[7:0]]."""
    return [register, (register_bits >> 8) & 0xFF, register_bits & 0xFF]


# EEPROM programming plumbing, resolved once so a table rename fails at import.
# Control words (register 161) are derived from the table so bit positions have
# a single source of truth: Erase = EN|ER = 3, Write = EN|WR = 5.
_EEPROM_ADDRESS_REGISTER = REGISTERS["EEPROM_ADDRESS"].register
_EEPROM_DATA_IN_REGISTER = REGISTERS["EEPROM_DATA_IN"].register
_EEPROM_CTRL_REGISTER = REGISTERS["EEPROM_EN"].register
_ERASE_CONTROL = REGISTERS["EEPROM_ER"].insert(REGISTERS["EEPROM_EN"].insert(0, 1), 1)
_WRITE_CONTROL = REGISTERS["EEPROM_WR"].insert(REGISTERS["EEPROM_EN"].insert(0, 1), 1)
_CONTROL_IDLE = 0


class A89301Driver:
    """Reads and writes A89301 fields by name over a real I2C bus (smbus2).

    Owns the bus for its lifetime (close via :meth:`close` or context manager).
    Writes are read-modify-write against the register bits read from the
    device just before each write. With ``use_cache=True`` that read is skipped
    when cached register bits exist — an opt-in for high-frequency writes
    which assumes this driver is the device's only writer and the device never resets
    (see :meth:`invalidate_cache`). Instances are thread-safe: a lock
    serializes bus and cache access.
    """

    def __init__(self, bus: int = 1, *, use_cache: bool = False) -> None:
        self._bus: SMBus | None = SMBus(bus)
        self._use_cache = use_cache
        self._cache: dict[int, int] = {}
        self._lock = threading.Lock()

    def close(self) -> None:
        """Release the owned I2C bus (idempotent).

        Any later read/write/persist raises A89301Error.
        """
        with self._lock:
            if self._bus is not None:
                self._bus.close()
                self._bus = None

    def __enter__(self) -> A89301Driver:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def read(self, name: str) -> int | float:
        """Read field ``name`` and return its physical value (raw when unscaled).

        Always hits the bus (readback values change on the device); with
        ``use_cache=True`` the fetched register bits also refresh the cache
        used by :meth:`write`. Raises UnknownFieldError for an unknown name.
        """
        field = self._get_field(name)
        with self._lock:
            register_bits = self._read_register(field.register)
            if self._use_cache:
                self._cache[field.register] = register_bits
        return field.decode(register_bits)

    def write(self, name: str, physical_value: int | float) -> int | float:
        """Write ``physical_value`` to the volatile register of field ``name`` (RMW).

        Symmetric with :meth:`read`: fields with a conversion take the physical
        value (rounded to the nearest raw step), unscaled fields take the raw
        int — so a value returned by ``read`` can be written back as-is.
        Returns the effective value actually written after rounding. Sibling
        fields sharing the register are preserved. The value is lost on power
        cycle unless followed by :meth:`persist`.

        Raises UnknownFieldError for an unknown field, NotWritableError for a
        read-only / factory-controlled / EEPROM-control register, and
        ValueRangeError when ``physical_value`` does not fit the field.
        """
        field = self._get_writable_field(name)
        raw_value = field.encode(physical_value)
        with self._lock:
            current = self._cache.get(field.register) if self._use_cache else None
            if current is None:
                current = self._read_register(field.register)
            merged = field.insert(current, raw_value)
            try:
                self._write_register(field.register, merged)
            except Exception:
                # The frame may or may not have reached the device; drop the
                # cached register bits so the next write re-reads instead of
                # doing RMW on a stale value.
                if self._use_cache:
                    logger.warning("write to register %d failed; cache dropped", field.register)
                    self._cache.pop(field.register, None)
                raise
            if self._use_cache:
                self._cache[field.register] = merged
        return field.decode(merged)

    def persist(self, name: str) -> None:
        """Program the current value of ``name``'s register into EEPROM.

        Persists all 16 register bits — the current volatile values of
        every field sharing the register, not just ``name`` (field names
        sharing a register are equivalent here) — via the datasheet Erase ->
        Write sequence (blocks ~30 ms). The register bits are always re-read
        from the device just before programming, so what burns is the device's
        actual state, never a cached one. Success is not verified by reading
        the EEPROM back.

        A ``write`` and a following ``persist`` are two separate lock scopes:
        with multiple threads, change and persist a register from the same
        thread. EEPROM endurance is limited; persist only state that must
        survive power cycles. If the sequence fails midway the EEPROM word may
        be left erased (reads as 0 after the next power-on) while the volatile
        register stays correct — recover by retrying ``persist(name)``.

        Raises UnknownFieldError for an unknown field and NotWritableError for
        a read-only / factory-controlled / EEPROM-control register.
        """
        field = self._get_writable_field(name)
        with self._lock:
            register_bits = self._read_register(field.register)
            if self._use_cache:
                self._cache[field.register] = register_bits
            self._program_eeprom(field.register - REGISTER_EEPROM_OFFSET, register_bits)

    def invalidate_cache(self, name: str | None = None) -> None:
        """Drop cached register bits (all, or field ``name``'s) to force re-reads.

        Only meaningful with ``use_cache=True``, where it is required after
        registers change behind the driver's back: a device reset
        (configuration reloads from EEPROM) or another master's writes.
        Without the cache this is a harmless no-op.
        """
        if name is None:
            with self._lock:
                self._require_bus()
                self._cache.clear()
        else:
            field = self._get_field(name)
            with self._lock:
                self._require_bus()
                self._cache.pop(field.register, None)

    def _require_bus(self) -> SMBus:
        if self._bus is None:
            raise A89301Error("driver is closed")
        return self._bus

    def _write_register(self, register: int, register_bits: int) -> None:
        """Send one write-command frame."""
        frame = _encode_write_frame(register, register_bits)
        logger.debug("write frame: %s", frame)
        self._require_bus().i2c_rdwr(i2c_msg.write(SLAVE_ADDRESS, frame))

    def _program_eeprom(self, address: int, register_bits: int) -> None:
        """Persist ``register_bits`` at EEPROM ``address``: Erase -> Write (datasheet).

        Each phase sets address (162) and data (163), triggers via control
        (161), then waits for the on-chip pulse to finish. Control is returned
        to idle afterwards; a failure to do so is raised (the programming
        voltage may still be enabled) unless the sequence itself already
        failed, in which case the original error wins and the idle failure is
        only logged.
        """
        try:
            for control, data, delay in (
                (_ERASE_CONTROL, 0, EEPROM_ERASE_DELAY_S),
                (_WRITE_CONTROL, register_bits, EEPROM_WRITE_DELAY_S),
            ):
                self._write_register(_EEPROM_ADDRESS_REGISTER, address)
                self._write_register(_EEPROM_DATA_IN_REGISTER, data)
                self._write_register(_EEPROM_CTRL_REGISTER, control)
                time.sleep(delay)
        except Exception:
            try:
                self._write_register(_EEPROM_CTRL_REGISTER, _CONTROL_IDLE)
            except Exception:
                logger.warning("failed to return EEPROM control to idle", exc_info=True)
            raise
        else:
            self._write_register(_EEPROM_CTRL_REGISTER, _CONTROL_IDLE)

    def _get_field(self, name: str) -> Field:
        try:
            return REGISTERS[name]
        except KeyError:
            raise UnknownFieldError(f"{name!r} is not a defined A89301 field") from None

    def _get_writable_field(self, name: str) -> Field:
        field = self._get_field(name)
        if field.register not in WRITABLE_REGISTERS:
            raise NotWritableError(f"{name!r} (register {field.register}) is not writable")
        return field

    def _read_register(self, register: int) -> int:
        """Read a register's 16 bits via two STOP-separated transactions (datasheet)."""
        bus = self._require_bus()
        write_msg = i2c_msg.write(SLAVE_ADDRESS, [register])
        read_msg = i2c_msg.read(SLAVE_ADDRESS, READ_LENGTH)
        bus.i2c_rdwr(write_msg)  # transaction 1, then STOP
        bus.i2c_rdwr(read_msg)  # transaction 2
        high, low = list(read_msg)
        register_bits = (high << 8) | low
        logger.debug("read register %d: 0x%04X", register, register_bits)
        return register_bits
