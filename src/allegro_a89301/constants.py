"""A89301 I2C protocol constants (datasheet)."""

from __future__ import annotations

SLAVE_ADDRESS: int = 0x55  # 7-bit I2C address (Device ID 1010101)

REGISTER_WIDTH: int = 16  # registers are 16-bit, MSB-first
REGISTER_BITS_MASK: int = (1 << REGISTER_WIDTH) - 1  # 0xFFFF
READ_LENGTH: int = REGISTER_WIDTH // 8  # bytes returned by a register read (2)

MAX_REGISTER_ADDRESS: int = 0xFF  # register addresses are a single byte (0..255)

REGISTER_EEPROM_OFFSET: int = 64  # register address = EEPROM address + 64

# Post-command settle times for EEPROM programming (datasheet: 15 ms HV erase
# pulse, ~10 ms per-word write; both held at 15 ms to stay on the safe side).
EEPROM_ERASE_DELAY_S: float = 0.015
EEPROM_WRITE_DELAY_S: float = 0.015
