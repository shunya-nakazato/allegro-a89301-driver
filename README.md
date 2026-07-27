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
4. **Read-modify-write safety** — writing one field of a multi-field register preserves the other fields (the driver reads the current word and replaces only the field's bits; an opt-in cache can spare the bus)

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

Not yet published to PyPI — install from a checkout of this repository:

```bash
pip install .   # depends on smbus2 for I2C access (Linux/Raspberry Pi)
```

For local development:

```bash
uv sync          # environment + dependencies
uv run pytest    # run the test suite (no hardware needed; smbus2 is patched)
```

`A89301Driver` owns the I2C connection (smbus2). `smbus2` is a required dependency.

## Usage

`A89301Driver` reads a field **by name** and returns its physical value (or the
raw integer for fields without a context-free conversion), coerced to the
field's declared type.

```python
from allegro_a89301 import A89301Driver

driver = A89301Driver(bus=1)  # opens /dev/i2c-1 and holds it

temp = driver.read("TEMPERATURE")  # 22.0 (degC)
speed = driver.read("MOTOR_SPEED")  # 530.0 (Hz)
mode = driver.read("I2C_SPD_MODE")  # 1 (raw bit)
```

The driver creates and owns the I2C bus in its constructor (no dependency
injection). Reads use two transactions with a STOP between them (per datasheet),
so smbus2 is driven via `i2c_rdwr`, not a repeated-start block read.

The bus is held for the driver's lifetime; call `close()` or use it as a context
manager to release the `/dev/i2c-N` handle:

```python
with A89301Driver(bus=1) as driver:
    temp = driver.read("TEMPERATURE")
```

### Writing fields

`write(name, value)` is **symmetric with `read`**: fields with a datasheet
conversion take the physical value (rounded to the nearest raw step), unscaled
fields take the raw int — so a value returned by `read` can be written back
as-is. Writes are **read-modify-write**: the driver fetches the current 16-bit
register word, replaces only the field's bits, and writes the merged word
back, so sibling fields sharing the register are preserved. `write` returns
the **effective value** actually written after rounding.

```python
with A89301Driver(bus=1) as driver:
    driver.write("RATED_SPEED", 530.0)  # physical value (Hz) -> raw 1000
    driver.write("I2C_SPD_MODE", 1)  # raw bit: speed demand from register 17[8:0]
    actual = driver.write("I2C_SPD_DEMAND", 50.0)  # percent -> raw 256 -> 50.09...
```

Register writes are volatile: the device reloads its configuration from EEPROM
at power-on.

### Persisting to EEPROM

`persist(name)` programs the **current word of `name`'s register** into the
matching EEPROM address (register − 64) via the datasheet Erase → Write
sequence, then returns control to idle:

```python
with A89301Driver(bus=1) as driver:
    driver.write("DIRECTION", 1)
    driver.persist("DIRECTION")  # survives power cycles
```

- The whole register word is persisted — the current volatile values of
  *every* field sharing the register, not just `name` (field names sharing a
  register are equivalent here: `persist("RATED_SPEED")` and
  `persist("DIRECTION")` do the same thing).
- The word is always **re-read from the device just before programming**, so
  what burns is the device's actual state, never a cached one. Success is not
  verified by reading the EEPROM back (a read-back check is future work).
- `write` and a following `persist` are separate lock scopes: with multiple
  threads, change and persist a register from the same thread, or another
  thread's write may land in between and get burned.
- The call blocks ~30 ms for the on-chip pulses. EEPROM endurance is limited:
  persist only state that must survive power cycles — not per-cycle speed
  demands.
- If the sequence fails midway the EEPROM word may be left erased (reads as 0
  after the next power-on) while the volatile register stays correct; recover
  by retrying `persist(name)`. A failure to return control to idle is raised
  too — the programming voltage may still be enabled, so it must not look
  like success.

### Optional register cache

By default every write re-reads the register from the device just before
merging, so RMW always builds on the device's actual state — safe even when
the device browns out and reloads its EEPROM configuration mid-session
(common around motors). The cost is one extra register read per write
(~0.5 ms on a 100 kHz bus).

For high-frequency writes (e.g. streaming `I2C_SPD_DEMAND` from a control
loop) you can opt into a per-register word cache:

```python
driver = A89301Driver(bus=1, use_cache=True)
```

The opt-in comes with a contract:

- The cache assumes this driver is the device's **only writer** and the
  device never resets. Repeated writes to a register skip the bus read;
  `read()` also refreshes the cache.
- After a device reset / power glitch or writes by another I2C master, call
  `invalidate_cache()` (optionally with a field name, e.g.
  `invalidate_cache("DIRECTION")`) so the next write re-reads the device.
  Without `use_cache=True` it is a harmless no-op.
- If sending a write frame raises, the register's cached word is dropped
  (logged as a warning) — the device may or may not have applied the frame,
  so the next write re-reads instead of merging into a stale word.

`persist` always re-reads the device regardless of this setting.

### Errors

All errors derive from `A89301Error` and double as the builtin they replaced:

- `UnknownFieldError` (also `KeyError`) — name not in the register table
- `NotWritableError` (also `ValueError`) — readback registers (120–127), the
  factory-controlled register 83 (EEPROM 19), and EEPROM control registers
  (161–163, driven only internally by `persist(name)`)
- `ValueRangeError` (also `ValueError`) — value doesn't fit the field,
  including a non-int value for a raw field

No frame is sent on rejection. Plain `A89301Error` is raised when the driver
is used after `close()`.

`A89301Driver` instances are thread-safe: a lock serializes bus and cache access
(`persist` holds it for ~30 ms), and `close()` is idempotent and safe against
concurrent operations. Frames are logged at DEBUG level via the
`allegro_a89301.driver` logger; a cache drop after a failed write is logged
as a warning.

### Structure
- `constants` — I2C protocol constants (slave address, register width, EEPROM timings)
- `errors` — the `A89301Error` exception hierarchy
- `field` — the `Field` bit-field type; decode/encode between raw words and typed values
- `registers` — field definitions (addresses, bit fields), conversions, and register access classification
- `driver` — `A89301Driver`, which owns the I2C connection and reads/writes fields by name

Public API: `A89301Driver`, `SLAVE_ADDRESS`, and the `errors` classes.

Current scope is **synchronous `read(name)` / `write(name, value)` / `persist(name)`**.
The context-dependent / non-linear read conversions (`MOTOR_RESISTANCE`,
current & acceleration scaling, `SPEED_RESPONSE_TC_AND_CLOCK_SPEED_RATIO`,
`OPERATION_STATE`, `MOSFET_CISS_COMP`) are not implemented yet; those fields
read and write as raw.

---

## References

- Pololu product page: https://www.pololu.com/product/5356
- A89301 datasheet: https://www.pololu.com/file/0J2192/A89301-Datasheet.pdf
