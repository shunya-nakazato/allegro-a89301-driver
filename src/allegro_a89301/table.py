"""A89301 register table (datasheet Table 1/2).

The ``Field`` type and conversions live in ``field.py``; this module holds the
register data. Each field carries its physical conversion (``None`` = raw) and its
read ``value_type`` (``int`` for raw enums/bitfields, ``float`` for scaled values).
"""

from __future__ import annotations

from allegro_a89301.field import Field

# Conversions: raw -> physical value (see datasheet Table 2).
_HZ = lambda raw: raw * 0.530
_V = lambda raw: raw / 5
_PCT = lambda raw: raw * 100 / 511  # 0..511 represents 0..100%
_DEADTIME = lambda raw: (raw + 1) * 40  # ns (reads as int)

# name -> Field; names follow the datasheet.
# 72..86 = config (mirror of EEPROM 8..22), 120..127 = readback, 161..163 = EEPROM ctrl.
REGISTERS: dict[str, Field] = {
    # Register 72 (EEPROM 8)
    "RATED_SPEED": Field("RATED_SPEED", 72, 10, 0, "Rated Speed (Hz)", _HZ, float),
    "SPEED_CLOSE_LOOP": Field("SPEED_CLOSE_LOOP", 72, 11, 11, "1: closed, 0: open loop"),
    "CLOCK_PWM": Field("CLOCK_PWM", 72, 12, 12, "1: clock mode, 0: PWM mode"),
    "ACCELERATE_RANGE": Field("ACCELERATE_RANGE", 72, 13, 13, "Acceleration range sel"),
    "DIRECTION": Field("DIRECTION", 72, 14, 14, "1: A->B->C, 0: A->C->B"),
    "PWMIN_RANGE": Field("PWMIN_RANGE", 72, 15, 15, "1: <=2.8 kHz, 0: >2.8 kHz"),
    # Register 73 (EEPROM 9)
    "ACCELERATION": Field("ACCELERATION", 73, 7, 0, "Acceleration (Hz/s) = value * k"),
    "MOTOR_RESISTANCE": Field("MOTOR_RESISTANCE", 73, 15, 8, "Motor resistance"),
    # Register 74 (EEPROM 10)
    "RATED_CURRENT": Field("RATED_CURRENT", 74, 10, 0, "Rated Current (mA) via sense R"),
    "SPD_MODE": Field("SPD_MODE", 74, 11, 11, "1: analog, 0: digital (PWM/clock)"),
    "STARTUP_CURRENT": Field("STARTUP_CURRENT", 74, 15, 13, "Startup current multiplier"),
    # Register 75 (EEPROM 11)
    "OPEN_DRIVE": Field("OPEN_DRIVE", 75, 3, 3, "See application note"),
    "DIRECT_DR_ANGLE": Field("DIRECT_DR_ANGLE", 75, 5, 5, "1: 12[12:8] sets phase angle"),
    "MAX_START_CURR": Field("MAX_START_CURR", 75, 6, 6, "See application note"),
    "POWER_CTL_EN": Field("POWER_CTL_EN", 75, 7, 7, "1: enable current limit"),
    "STARTUP_MODE": Field("STARTUP_MODE", 75, 11, 10, "00:6p 01:2p 10:slight 11:align"),
    "WAIT_STATIONARY": Field("WAIT_STATIONARY", 75, 12, 12, "See application note"),
    "EXTEND_LOCK_MASK": Field("EXTEND_LOCK_MASK", 75, 14, 14, "See application note"),
    # Register 76 (EEPROM 12)
    "PID_P": Field("PID_P", 76, 7, 0, "Position observer loop P gain"),
    "MOTOR_INDUCTANCE": Field("MOTOR_INDUCTANCE", 76, 12, 8, "5-bit: [3:0]@11:8 + [4]@12"),
    "OVER_SPEED_LOCK": Field("OVER_SPEED_LOCK", 76, 13, 13, "See application note"),
    "OPEN_WINDOW": Field("OPEN_WINDOW", 76, 15, 15, "1: open window for L tuning"),
    # Register 77 (EEPROM 13)
    "PID_I": Field("PID_I", 77, 7, 0, "Position observer loop I gain"),
    "DELAY_START": Field("DELAY_START", 77, 13, 13, "1: delayed start"),
    # Register 78 (EEPROM 14)
    "FG_PIN_DIS": Field("FG_PIN_DIS", 78, 4, 4, "1: FG pin always high (eases I2C)"),
    # Register 79 (EEPROM 15)
    "ANGLE_ERROR_LOCK": Field("ANGLE_ERROR_LOCK", 79, 3, 2, "Lock detect during startup"),
    "SOFT_OFF": Field("SOFT_OFF", 79, 6, 6, "See functional description"),
    "SOFT_ON": Field("SOFT_ON", 79, 7, 7, "See functional description"),
    # DEADTIME_SETTING has a conversion but reads as int, so value_type stays int.
    "DEADTIME_SETTING": Field("DEADTIME_SETTING", 79, 11, 8, "(n+1)*40 ns", _DEADTIME),
    "SAFE_BRAKE_THRD": Field("SAFE_BRAKE_THRD", 79, 15, 14, "00:1x 01:2x 10:4x 11:8x I"),
    # Register 80 (EEPROM 16)
    "OCP_ENABLE": Field("OCP_ENABLE", 80, 2, 0, "100: 480 ns filter, 111: disabled"),
    "OCP_RESET_MODE": Field("OCP_RESET_MODE", 80, 3, 3, "0: on restart, 1: after 5 s"),
    "OCP_MASKING": Field("OCP_MASKING", 80, 5, 4, "00:none 01:320 10:640 11:1280 ns"),
    "FIRST_CYCLE_SPEED": Field("FIRST_CYCLE_SPEED", 80, 7, 6, "00:.55 01:1.1 10:2.2 11:4.4"),
    "ACCELERATE_BUFFER": Field("ACCELERATE_BUFFER", 80, 9, 8, "See application note"),
    "DECELERATE_BUFFER": Field("DECELERATE_BUFFER", 80, 11, 10, "See application note"),
    "BEMF_LOCK_FILTER": Field("BEMF_LOCK_FILTER", 80, 13, 12, "See application note"),
    # Register 81 (EEPROM 17)
    "I2C_SPD_DEMAND": Field("I2C_SPD_DEMAND", 81, 8, 0, "0..511 = 0..100%", _PCT, float),
    "I2C_SPD_MODE": Field("I2C_SPD_MODE", 81, 9, 9, "0: SPD pin, 1: register 81[8:0]"),
    # Register 82 (EEPROM 18)
    "IPD_CURRENT_THR": Field(
        "IPD_CURRENT_THR", 82, 13, 8, "IPD thr (A)", lambda raw: raw * 0.086, float
    ),
    "DRIVE_GATE_SLEW": Field("DRIVE_GATE_SLEW", 82, 15, 14, "Gate slew selector"),
    # Register 83 (EEPROM 19) -- factory controlled
    "MOSFET_CISS_COMP": Field("MOSFET_CISS_COMP", 83, 15, 8, "MOSFET Ciss compensation"),
    # Register 84 (EEPROM 20)
    "RATED_VOLTAGE": Field("RATED_VOLTAGE", 84, 7, 0, "Rated Voltage (V)", _V, float),
    "SENSE_RESISTOR": Field(
        "SENSE_RESISTOR", 84, 15, 8, "Sense R (mOhm)", lambda raw: raw / 3.7, float
    ),
    # Register 85 (EEPROM 21)
    "SLIGHT_MV_DEMAND": Field(
        "SLIGHT_MV_DEMAND", 85, 7, 5, "Amplitude (%)", lambda raw: raw * 3.2 + 2.4, float
    ),
    "SPEED_INPUT_OFF_THRESHOLD": Field(
        "SPEED_INPUT_OFF_THRESHOLD", 85, 9, 8, "00:10 01:6 10:15 11:20 %"
    ),
    "STANDBY_DIS": Field("STANDBY_DIS", 85, 15, 15, "0: standby enabled, 1: disabled"),
    # Register 86 (EEPROM 22)
    "SPEED_RESPONSE_TC_AND_CLOCK_SPEED_RATIO": Field(
        "SPEED_RESPONSE_TC_AND_CLOCK_SPEED_RATIO", 86, 5, 0, "TC / clock ratio"
    ),
    "RESTART_ATTEMPT": Field("RESTART_ATTEMPT", 86, 7, 6, "00:always 01:3 10:5 11:10"),
    "BRAKE_MODE": Field("BRAKE_MODE", 86, 8, 8, "0: brake when safe, 1: uncontrolled"),
    "SOFT_OFF_TIME": Field("SOFT_OFF_TIME", 86, 9, 9, "1: 4 seconds, 0: 1 second"),
    "VIBRATION_LOCK": Field("VIBRATION_LOCK", 86, 10, 10, "See application note"),
    "LOCK_RESTART_SET": Field("LOCK_RESTART_SET", 86, 11, 11, "0: 5 seconds, 1: 10 seconds"),
    "DEADTIME_COMP": Field("DEADTIME_COMP", 86, 12, 12, "1: enable deadtime compensation"),
    "VDS_THRESHOLD_SEL": Field("VDS_THRESHOLD_SEL", 86, 15, 15, "1: 2 V, 0: 1 V"),
    # Readback registers (read-only)
    "MOTOR_SPEED": Field("MOTOR_SPEED", 120, 15, 0, "Motor Speed (Hz)", _HZ, float),
    "BUS_CURRENT": Field("BUS_CURRENT", 121, 15, 0, "Bus current (mA) via sense R"),
    "Q_AXIS_CURRENT": Field("Q_AXIS_CURRENT", 122, 15, 0, "Q-axis current (mA) via sense R"),
    "VBB": Field("VBB", 123, 15, 0, "VBB (V)", _V, float),
    "TEMPERATURE": Field(
        "TEMPERATURE", 124, 15, 0, "Temperature (degC)", lambda raw: raw - 53.0, float
    ),
    "CONTROL_DEMAND": Field("CONTROL_DEMAND", 125, 8, 0, "0..511 = 0..100%", _PCT, float),
    "CONTROL_COMMAND": Field("CONTROL_COMMAND", 126, 8, 0, "0..511 = 0..100%", _PCT, float),
    "OPERATION_STATE": Field("OPERATION_STATE", 127, 15, 12, "Operation state"),
    # EEPROM programming registers
    "EEPROM_EN": Field("EEPROM_EN", 161, 0, 0, "Set EEPROM voltage for write/erase"),
    "EEPROM_ER": Field("EEPROM_ER", 161, 1, 1, "Erase mode"),
    "EEPROM_WR": Field("EEPROM_WR", 161, 2, 2, "Write mode"),
    "EEPROM_RD": Field("EEPROM_RD", 161, 3, 3, "Read mode"),
    "EEPROM_ADDRESS": Field("EEPROM_ADDRESS", 162, 4, 0, "EEPROM address to alter"),
    "EEPROM_DATA_IN": Field("EEPROM_DATA_IN", 163, 15, 0, "EEPROM data to program"),
}
