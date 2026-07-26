# Allegro A89301 Motor Drive — I2C Command Library

A library for controlling Pololu's [A89301-based sensorless BLDC motor controller board (#5356)](https://www.pololu.com/product/5356) over I2C. It handles **command generation (encoding)** and **response parsing** for the Allegro A89301 I2C protocol, making register/EEPROM reads and writes type-safe and concise.

- Product page: https://www.pololu.com/product/5356
- Datasheet: [A89301 Datasheet (PDF)](https://www.pololu.com/file/0J2192/A89301-Datasheet.pdf)

---

## Target Hardware

An FOC (Field-Oriented Control) controller for 3-phase sensorless BLDC motors, built around the Allegro **A89301** (50V Ultra Low Noise FOC Motor Controller).

| Item | Details |
|---|---|
| Motor type | 3-phase sensorless BLDC (sinusoidal FOC drive) |
| Operating voltage | 5.5V–48V (50V absolute max) |
| Continuous current | Up to 11A (phase amplitude) |
| Control interfaces | Analog voltage / PWM duty / pulse frequency (CLOCK) / **I2C** |
| Configuration storage | Non-volatile EEPROM (loaded into registers at power-on) |

Speed can be commanded via analog, PWM, or CLOCK inputs, but this library targets **configuration and control over I2C**. Using I2C, the EEPROM defaults can be overwritten in the registers and parameters changed on the fly.

> Note: Until the first I2C command is sent, the SPD pin acts as SCL and the FG pin as SDA. After the first I2C command, the FG pin becomes a dedicated data pin (SDA).

---

## Purpose of the Library

The A89301 I2C protocol has a simple structure — "7-bit slave address + 8-bit register address + 16-bit data (MSB first)" — but the following tend to be error-prone in practice. This library takes care of them:

1. **Command generation (encoding)** — build the byte sequence (I2C frame) for register writes and reads
2. **Response parsing** — convert the 2 read bytes into physical quantities (Hz, V, °C, etc.)
3. **Physical value ⇄ register value conversion** — handle the datasheet conversion formulas (e.g. `Rated Speed (Hz) = value × 0.530`) in a type-safe way
4. **Read-modify-write safety** — writing one field of a multi-field register preserves the other fields (via the required `base_word`)

---

## I2C Protocol (per Datasheet)

### Slave address
- 7-bit slave address: **`0x55`** (Device ID `1010101`)
- Register data is a fixed **16 bits, MSB first**

### Write command
```
START
  → Peripheral Address (0x55, R/W=0)      ; ACK
  → Register Address (8-bit)              ; ACK
  → Data Byte 2 = D[15:8] (high byte)     ; ACK
  → Data Byte 1 = D[7:0]  (low byte)      ; ACK
STOP
```

### Read command (two steps)
```
START → Peripheral Address (0x55, R/W=0) ; ACK
  → Register Address (8-bit)             ; ACK
STOP
START → Slave Address (0x55, R/W=1)      ; ACK
  → Read Data Byte 2 = D[15:8]           ; ACK
  → Read Data Byte 1 = D[7:0]            ; NACK
STOP
```

### Register / EEPROM address relationship
- The EEPROM holds 24 words × 16 bits. Users work with **addresses 8–22** (configuration).
- **Register address = corresponding EEPROM address + 64**
  Example: Rated Speed is at EEPROM `8`; its register address is `72`.
- Writing over I2C to a register overwrites the live value (volatile, takes effect immediately); writing to EEPROM persists across power cycles.

---

## Key Registers (excerpt)

### Configuration registers (EEPROM 8–22 / registers 72–86)
| Reg | Parameter | Conversion / meaning |
|---|---|---|
| 8 [10:0] | `RATED_SPEED` | Rated Speed (Hz) = value × 0.530 |
| 8 [11] | `SPEED_CLOSE_LOOP` | 1: closed loop / 0: open loop |
| 8 [14] | `DIRECTION` | 1: A→B→C / 0: A→C→B |
| 9 [7:0] | `ACCELERATION` | Hz/s = value × k (range=0 → k=0.05, else 3.2) |
| 10 [10:0] | `RATED_CURRENT` | mA = value / (Sense_resistor / 125) |
| 11 [11:10] | `STARTUP_MODE` | 00: 6-pulse / 01: 2-pulse / 10: slight-move / 11: align & go |
| 17 [8:0] | `I2C_SPD_DEMAND` | 0–511 → 0–100% |
| 17 [9] | `I2C_SPD_MODE` | 0: controlled by SPD pin / 1: controlled by register 17[8:0] |
| 20 [7:0] | `RATED_VOLTAGE` | V = value / 5 |
| 20 [15:8] | `SENSE_RESISTOR` | mΩ = value / 3.7 |

> Bits marked gray in the datasheet (Table 1) must be kept at their defaults. Writing to undocumented registers may cause malfunction or damage, so the library does not touch them.

### Readback registers
| Reg | Content | Conversion |
|---|---|---|
| 120 | Motor speed | Hz = value × 0.530 |
| 121 | Bus current | mA = value / (Sense_resistor / 125) |
| 122 | Q-axis current | mA = value / (Sense_resistor / 125) |
| 123 | VBB | V = value / 5 |
| 124 | Temperature | °C = value − 53 |
| 125 | Control demand | 0–511 → 0–100% |
| 126 | Control command | 0–511 → 0–100% |
| 127 [15:12] | Operation state | operating state |

### EEPROM programming registers
| Reg | Name | Purpose |
|---|---|---|
| 161 | EEPROM Control | bit0 `EN` / bit1 `ER` (Erase) / bit2 `WR` (Write) / bit3 `RD` (Read) |
| 162 | EEPROM Address | `eeADDRESS` (addresses 0 and 19 are factory-controlled — do not change) |
| 163 | EEPROM DATA_IN | data to write (16-bit) |

The EEPROM is rewritten one word at a time via "Erase → Write". Each operation takes about 10 ms (Erase requires a 15 ms high-voltage pulse).

---

## Installation

Python 3.12+ library, managed with [uv](https://docs.astral.sh/uv/).

```bash
pip install allegro-a89301   # depends on smbus2 for I2C access (Linux/Raspberry Pi)
```

For local development:

```bash
uv sync          # environment + dependencies
uv run pytest    # run the test suite (no hardware needed; smbus2 is patched)
```

`I2CDriver` owns the I2C connection (smbus2). `smbus2` is a required dependency.

## Usage

`I2CDriver` reads a field **by name** and returns a `Reading(name, value)`, where
`value` is the physical value (or the raw integer for fields without a
context-free conversion), coerced to the field's declared type.

```python
from allegro_a89301 import I2CDriver

driver = I2CDriver(bus=1)  # opens /dev/i2c-1 and holds it

temp = driver.read("TEMPERATURE")  # Reading(name="TEMPERATURE", value=22.0)
speed = driver.read("MOTOR_SPEED")  # Reading(name="MOTOR_SPEED", value=530.0)
mode = driver.read("I2C_SPD_MODE")  # Reading(name="I2C_SPD_MODE", value=1)  # raw bit

celsius = temp.value  # 22.0
```

The driver creates and owns the I2C bus in its constructor (no dependency
injection). Reads use two transactions with a STOP between them (per datasheet),
so smbus2 is driven via `i2c_rdwr`, not a repeated-start block read.

The bus is held for the driver's lifetime; call `close()` or use it as a context
manager to release the `/dev/i2c-N` handle:

```python
with I2CDriver(bus=1) as driver:
    temp = driver.read("TEMPERATURE")
```

### Structure
- `constants` — I2C protocol constants (slave address, register width)
- `field` — the `Field` bit-field type and `Reading`; decodes a raw word into a typed value
- `table` — field definitions (addresses, bit fields) and context-free conversions
- `driver` — `I2CDriver`, which owns the I2C connection and reads fields by name

Public API: `I2CDriver`, `Reading`, `SLAVE_ADDRESS`.

Current scope is **synchronous `read(name)`**. Writes, EEPROM programming, and the
context-dependent / non-linear conversions (`MOTOR_RESISTANCE`, current &
acceleration scaling, `SPEED_RESPONSE_TC_AND_CLOCK_SPEED_RATIO`, `OPERATION_STATE`,
`MOSFET_CISS_COMP`) are not implemented yet; those fields read as raw.

---

## References

- Pololu product page: https://www.pololu.com/product/5356
- A89301 datasheet: https://www.pololu.com/file/0J2192/A89301-Datasheet.pdf
