"""A89301 register table (datasheet Table 1/2) and access classification.

Each field carries its raw<->physical conversions (``None`` = used raw) and
its read ``physical_type``; the ``Field`` type itself lives in ``field.py``.
"""

from __future__ import annotations

from allegro_a89301.field import Field

# Conversions raw_value -> physical_value and their inverses (see datasheet
# Table 2). Writable fields carry both so read and write speak physical units;
# inverse results are rounded to the nearest raw step by Field.encode.
_HZ = lambda raw_value: raw_value * 0.530
_HZ_INV = lambda hz: hz / 0.530
_V = lambda raw_value: raw_value / 5
_V_INV = lambda v: v * 5
_PCT = lambda raw_value: raw_value * 100 / 511  # 0..511 represents 0..100%
_PCT_INV = lambda pct: pct * 511 / 100
_DEADTIME = lambda raw_value: (raw_value + 1) * 40  # ns (reads as int)
_DEADTIME_INV = lambda ns: ns / 40 - 1

# name -> Field; names follow the datasheet, which is also the source of the
# per-field descriptions in the trailing comments.
# 72..86 = config (mirror of EEPROM 8..22), 120..127 = readback, 161..163 = EEPROM ctrl.
REGISTERS: dict[str, Field] = {
    # Register 72 (EEPROM 8)
    "RATED_SPEED": Field(72, 10, 0, _HZ, float, _HZ_INV),  # Rated Speed (Hz)
    "SPEED_CLOSE_LOOP": Field(72, 11, 11),  # 1: closed, 0: open loop
    "CLOCK_PWM": Field(72, 12, 12),  # 1: clock mode, 0: PWM mode
    "ACCELERATE_RANGE": Field(72, 13, 13),  # Acceleration range sel
    "DIRECTION": Field(72, 14, 14),  # 1: A->B->C, 0: A->C->B
    "PWMIN_RANGE": Field(72, 15, 15),  # 1: <=2.8 kHz, 0: >2.8 kHz
    # Register 73 (EEPROM 9)
    "ACCELERATION": Field(73, 7, 0),  # Acceleration (Hz/s) = value * k
    "MOTOR_RESISTANCE": Field(73, 15, 8),  # Motor resistance
    # Register 74 (EEPROM 10)
    "RATED_CURRENT": Field(74, 10, 0),  # Rated Current (mA) via sense R
    "SPD_MODE": Field(74, 11, 11),  # 1: analog, 0: digital (PWM/clock)
    "STARTUP_CURRENT": Field(74, 15, 13),  # Startup current multiplier
    # Register 75 (EEPROM 11)
    "OPEN_DRIVE": Field(75, 3, 3),  # See application note
    "DIRECT_DR_ANGLE": Field(75, 5, 5),  # 1: 12[12:8] sets phase angle
    "MAX_START_CURR": Field(75, 6, 6),  # See application note
    "POWER_CTL_EN": Field(75, 7, 7),  # 1: enable current limit
    "STARTUP_MODE": Field(75, 11, 10),  # 00:6p 01:2p 10:slight 11:align
    "WAIT_STATIONARY": Field(75, 12, 12),  # See application note
    "EXTEND_LOCK_MASK": Field(75, 14, 14),  # See application note
    # Register 76 (EEPROM 12)
    "PID_P": Field(76, 7, 0),  # Position observer loop P gain
    "MOTOR_INDUCTANCE": Field(76, 12, 8),  # 5-bit: [3:0]@11:8 + [4]@12
    "OVER_SPEED_LOCK": Field(76, 13, 13),  # See application note
    "OPEN_WINDOW": Field(76, 15, 15),  # 1: open window for L tuning
    # Register 77 (EEPROM 13)
    "PID_I": Field(77, 7, 0),  # Position observer loop I gain
    "DELAY_START": Field(77, 13, 13),  # 1: delayed start
    # Register 78 (EEPROM 14)
    "FG_PIN_DIS": Field(78, 4, 4),  # 1: FG pin always high (eases I2C)
    # Register 79 (EEPROM 15)
    "ANGLE_ERROR_LOCK": Field(79, 3, 2),  # Lock detect during startup
    "SOFT_OFF": Field(79, 6, 6),  # See functional description
    "SOFT_ON": Field(79, 7, 7),  # See functional description
    # DEADTIME_SETTING: (n+1)*40 ns — scaled by raw_to_physical but reads as int.
    "DEADTIME_SETTING": Field(79, 11, 8, _DEADTIME, int, _DEADTIME_INV),
    "SAFE_BRAKE_THRD": Field(79, 15, 14),  # 00:1x 01:2x 10:4x 11:8x I
    # Register 80 (EEPROM 16)
    "OCP_ENABLE": Field(80, 2, 0),  # 100: 480 ns filter, 111: disabled
    "OCP_RESET_MODE": Field(80, 3, 3),  # 0: on restart, 1: after 5 s
    "OCP_MASKING": Field(80, 5, 4),  # 00:none 01:320 10:640 11:1280 ns
    "FIRST_CYCLE_SPEED": Field(80, 7, 6),  # 00:.55 01:1.1 10:2.2 11:4.4
    "ACCELERATE_BUFFER": Field(80, 9, 8),  # See application note
    "DECELERATE_BUFFER": Field(80, 11, 10),  # See application note
    "BEMF_LOCK_FILTER": Field(80, 13, 12),  # See application note
    # Register 81 (EEPROM 17)
    "I2C_SPD_DEMAND": Field(81, 8, 0, _PCT, float, _PCT_INV),  # 0..511 = 0..100%
    "I2C_SPD_MODE": Field(81, 9, 9),  # 0: SPD pin, 1: register 81[8:0]
    # Register 82 (EEPROM 18)
    "IPD_CURRENT_THR": Field(
        82, 13, 8, lambda raw_value: raw_value * 0.086, float, lambda amps: amps / 0.086
    ),  # IPD thr (A)
    "DRIVE_GATE_SLEW": Field(82, 15, 14),  # Gate slew selector
    # Register 83 (EEPROM 19) -- factory controlled
    "MOSFET_CISS_COMP": Field(83, 15, 8),  # MOSFET Ciss compensation
    # Register 84 (EEPROM 20)
    "RATED_VOLTAGE": Field(84, 7, 0, _V, float, _V_INV),  # Rated Voltage (V)
    "SENSE_RESISTOR": Field(
        84, 15, 8, lambda raw_value: raw_value / 3.7, float, lambda mohm: mohm * 3.7
    ),  # Sense R (mOhm)
    # Register 85 (EEPROM 21)
    "SLIGHT_MV_DEMAND": Field(
        85, 7, 5, lambda raw_value: raw_value * 3.2 + 2.4, float, lambda pct: (pct - 2.4) / 3.2
    ),  # Amplitude (%)
    "SPEED_INPUT_OFF_THRESHOLD": Field(85, 9, 8),  # 00:10 01:6 10:15 11:20 %
    "STANDBY_DIS": Field(85, 15, 15),  # 0: standby enabled, 1: disabled
    # Register 86 (EEPROM 22)
    "SPEED_RESPONSE_TC_AND_CLOCK_SPEED_RATIO": Field(86, 5, 0),  # TC / clock ratio
    "RESTART_ATTEMPT": Field(86, 7, 6),  # 00:always 01:3 10:5 11:10
    "BRAKE_MODE": Field(86, 8, 8),  # 0: brake when safe, 1: uncontrolled
    "SOFT_OFF_TIME": Field(86, 9, 9),  # 1: 4 seconds, 0: 1 second
    "VIBRATION_LOCK": Field(86, 10, 10),  # See application note
    "LOCK_RESTART_SET": Field(86, 11, 11),  # 0: 5 seconds, 1: 10 seconds
    "DEADTIME_COMP": Field(86, 12, 12),  # 1: enable deadtime compensation
    "VDS_THRESHOLD_SEL": Field(86, 15, 15),  # 1: 2 V, 0: 1 V
    # Readback registers (read-only)
    "MOTOR_SPEED": Field(120, 15, 0, _HZ, float),  # Motor Speed (Hz)
    "BUS_CURRENT": Field(121, 15, 0),  # Bus current (mA) via sense R
    "Q_AXIS_CURRENT": Field(122, 15, 0),  # Q-axis current (mA) via sense R
    "VBB": Field(123, 15, 0, _V, float),  # VBB (V)
    "TEMPERATURE": Field(124, 15, 0, lambda raw_value: raw_value - 53.0, float),  # Temp (degC)
    "CONTROL_DEMAND": Field(125, 8, 0, _PCT, float),  # 0..511 = 0..100%
    "CONTROL_COMMAND": Field(126, 8, 0, _PCT, float),  # 0..511 = 0..100%
    "OPERATION_STATE": Field(127, 15, 12),  # Operation state
    # EEPROM programming registers
    "EEPROM_EN": Field(161, 0, 0),  # Set EEPROM voltage for write/erase
    "EEPROM_ER": Field(161, 1, 1),  # Erase mode
    "EEPROM_WR": Field(161, 2, 2),  # Write mode
    "EEPROM_RD": Field(161, 3, 3),  # Read mode
    "EEPROM_ADDRESS": Field(162, 4, 0),  # EEPROM address to alter
    "EEPROM_DATA_IN": Field(163, 15, 0),  # EEPROM data to program
}

# Register-level access classification (datasheet). Kept next to the table so
# adding a register means classifying it here; the table spec enforces that
# every register above belongs to exactly one class.
CONFIG_REGISTERS = range(72, 87)  # mirror of EEPROM addresses 8..22
READBACK_REGISTERS = range(120, 128)  # read-only telemetry
EEPROM_CTRL_REGISTERS = range(161, 164)  # driven only by the persist sequence

# EEPROM 19 (register 83) is factory controlled; writing it may damage the device.
FACTORY_PROTECTED_REGISTERS: frozenset[int] = frozenset({83})

# Registers the generic write() may touch. Readback is read-only, and EEPROM
# control is excluded so a stray write() cannot assemble an erase sequence
# against the factory-controlled EEPROM words (0/19).
WRITABLE_REGISTERS: frozenset[int] = frozenset(CONFIG_REGISTERS) - FACTORY_PROTECTED_REGISTERS
