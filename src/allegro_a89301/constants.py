"""A89301 I2C protocol constants (datasheet)."""

from __future__ import annotations

SLAVE_ADDRESS: int = 0x55  # 7-bit I2C address (Device ID 1010101)

REGISTER_DATA_BITS: int = 16  # registers are 16-bit, MSB-first
WORD_MASK: int = (1 << REGISTER_DATA_BITS) - 1  # 0xFFFF
READ_LENGTH: int = REGISTER_DATA_BITS // 8  # bytes returned by a register read (2)

MAX_REGISTER_ADDRESS: int = 0xFF  # register addresses are a single byte (0..255)
