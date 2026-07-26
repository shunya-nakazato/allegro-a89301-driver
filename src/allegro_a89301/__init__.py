"""I2C command generation and parsing for the Allegro A89301 motor controller.

``I2CDriver`` is the primary interface: it owns the I2C connection and reads
fields by name, driven by the field table in ``allegro_a89301.table``.
"""

from allegro_a89301.constants import SLAVE_ADDRESS
from allegro_a89301.driver import I2CDriver
from allegro_a89301.field import Reading

__all__ = ["SLAVE_ADDRESS", "I2CDriver", "Reading"]
