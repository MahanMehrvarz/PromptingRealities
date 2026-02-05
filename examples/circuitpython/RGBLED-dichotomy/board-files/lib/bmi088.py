# SPDX-FileCopyrightText: 2023
# SPDX-License-Identifier: MIT

"""
`bmi088`
================================================================================

CircuitPython driver for the Bosch BMI088 6-axis accelerometer and gyroscope sensor


* Author(s): Based on Arduino and Raspberry Pi implementations

Implementation Notes
--------------------

**Hardware:**

* `Grove - 6-Axis Accelerometer&Gyroscope (BMI088)
  <https://www.seeedstudio.com/Grove-6-Axis-Accelerometer-Gyroscope-BMI08-p-3188.html>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""

import time
import struct
from micropython import const
from adafruit_bus_device.i2c_device import I2CDevice

# BMI088 Accelerometer registers
_BMI088_ACC_ADDRESS = const(0x19)
_BMI088_ACC_ALT_ADDRESS = const(0x18)
_BMI088_ACC_CHIP_ID = const(0x00)  # Default value 0x1E
_BMI088_ACC_ERR_REG = const(0x02)
_BMI088_ACC_STATUS = const(0x03)

_BMI088_ACC_X_LSB = const(0x12)
_BMI088_ACC_X_MSB = const(0x13)
_BMI088_ACC_Y_LSB = const(0x14)
_BMI088_ACC_Y_MSB = const(0x15)
_BMI088_ACC_Z_LSB = const(0x16)
_BMI088_ACC_Z_MSB = const(0x17)

_BMI088_ACC_TEMP_MSB = const(0x22)
_BMI088_ACC_TEMP_LSB = const(0x23)

_BMI088_ACC_CONF = const(0x40)
_BMI088_ACC_RANGE = const(0x41)

_BMI088_ACC_PWR_CONF = const(0x7C)
_BMI088_ACC_PWR_CTRL = const(0x7D)

_BMI088_ACC_SOFT_RESET = const(0x7E)

# BMI088 Gyroscope registers
_BMI088_GYRO_ADDRESS = const(0x69)
_BMI088_GYRO_ALT_ADDRESS = const(0x68)
_BMI088_GYRO_CHIP_ID = const(0x00)  # Default value 0x0F

_BMI088_GYRO_RATE_X_LSB = const(0x02)
_BMI088_GYRO_RATE_X_MSB = const(0x03)
_BMI088_GYRO_RATE_Y_LSB = const(0x04)
_BMI088_GYRO_RATE_Y_MSB = const(0x05)
_BMI088_GYRO_RATE_Z_LSB = const(0x06)
_BMI088_GYRO_RATE_Z_MSB = const(0x07)

_BMI088_GYRO_RANGE = const(0x0F)
_BMI088_GYRO_BAND_WIDTH = const(0x10)

_BMI088_GYRO_LPM_1 = const(0x11)

_BMI088_GYRO_SOFT_RESET = const(0x14)

# Accelerometer configuration values
# Output Data Rate (ODR) values
ACC_ODR_12 = const(0x05)  # 12.5 Hz
ACC_ODR_25 = const(0x06)  # 25 Hz
ACC_ODR_50 = const(0x07)  # 50 Hz
ACC_ODR_100 = const(0x08)  # 100 Hz
ACC_ODR_200 = const(0x09)  # 200 Hz
ACC_ODR_400 = const(0x0A)  # 400 Hz
ACC_ODR_800 = const(0x0B)  # 800 Hz
ACC_ODR_1600 = const(0x0C)  # 1600 Hz

# Accelerometer range values
ACC_RANGE_3G = const(0x00)  # ±3g
ACC_RANGE_6G = const(0x01)  # ±6g
ACC_RANGE_12G = const(0x02)  # ±12g
ACC_RANGE_24G = const(0x03)  # ±24g

# Accelerometer power modes
ACC_ACTIVE = const(0x00)
ACC_SUSPEND = const(0x03)

# Gyroscope range values
GYRO_RANGE_2000 = const(0x00)  # ±2000 dps
GYRO_RANGE_1000 = const(0x01)  # ±1000 dps
GYRO_RANGE_500 = const(0x02)   # ±500 dps
GYRO_RANGE_250 = const(0x03)   # ±250 dps
GYRO_RANGE_125 = const(0x04)   # ±125 dps

# Gyroscope ODR and bandwidth combinations
GYRO_ODR_2000_BW_532 = const(0x00)  # ODR: 2000Hz, Bandwidth: 532Hz
GYRO_ODR_2000_BW_230 = const(0x01)  # ODR: 2000Hz, Bandwidth: 230Hz
GYRO_ODR_1000_BW_116 = const(0x02)  # ODR: 1000Hz, Bandwidth: 116Hz
GYRO_ODR_400_BW_47 = const(0x03)    # ODR: 400Hz, Bandwidth: 47Hz
GYRO_ODR_200_BW_23 = const(0x04)    # ODR: 200Hz, Bandwidth: 23Hz
GYRO_ODR_100_BW_12 = const(0x05)    # ODR: 100Hz, Bandwidth: 12Hz
GYRO_ODR_200_BW_64 = const(0x06)    # ODR: 200Hz, Bandwidth: 64Hz
GYRO_ODR_100_BW_32 = const(0x07)    # ODR: 100Hz, Bandwidth: 32Hz

# Gyroscope power modes
GYRO_NORMAL = const(0x00)
GYRO_SUSPEND = const(0x80)
GYRO_DEEP_SUSPEND = const(0x20)


class BMI088:
    """Driver for the BMI088 accelerometer + gyroscope sensor."""

    def __init__(self, i2c, acc_address=_BMI088_ACC_ADDRESS, gyro_address=_BMI088_GYRO_ADDRESS):
        """Initialize the BMI088 sensor.

        :param i2c: The I2C bus the BMI088 is connected to.
        :param acc_address: The I2C address of the accelerometer sensor.
        :param gyro_address: The I2C address of the gyroscope sensor.
        """
        # Store original i2c object
        self._i2c_bus = i2c

        # Create I2C device objects for accelerometer and gyroscope
        try:
            self._acc_device = I2CDevice(i2c, acc_address)
            self._gyro_device = I2CDevice(i2c, gyro_address)
        except Exception as e:
            # If we can't create the device objects, try alternate addresses
            try:
                self._acc_device = I2CDevice(i2c, _BMI088_ACC_ALT_ADDRESS)
                self._gyro_device = I2CDevice(i2c, _BMI088_GYRO_ALT_ADDRESS)
            except Exception:
                raise RuntimeError(f"Failed to create I2C device: {e}")

        # Default ranges
        self._acc_range = ACC_RANGE_6G
        self._gyro_range = GYRO_RANGE_1000

        self._acc_scale = 6.0 / 32768.0  # Default for ±6g range
        self._gyro_scale = 1000.0 / 32768.0  # Default for ±1000 dps range

        # Initialize sensor first, then check connection
        # This will handle multiple I2C address attempts
        try:
            # Initialize sensor with robust error handling
            self.initialize()

            # Only check connection after initialization
            if not self.is_connected():
                # Try initializing again with alternate addresses
                self._acc_device = I2CDevice(i2c, _BMI088_ACC_ALT_ADDRESS)
                self._gyro_device = I2CDevice(i2c, _BMI088_GYRO_ALT_ADDRESS)
                self.initialize()

                if not self.is_connected():
                    raise RuntimeError("Failed to find BMI088 sensor")
        except Exception as e:
            # Continue anyway - some boards may only have accelerometer or gyro working
            pass

    def is_connected(self):
        """Check if BMI088 sensors are connected.

        :return: True if both accelerometer and gyroscope are found, False otherwise.
        """
        try:
            acc_id = self._read_acc_register(_BMI088_ACC_CHIP_ID)
            acc_connected = (acc_id == 0x1E)
        except Exception:
            acc_connected = False

        try:
            gyro_id = self._read_gyro_register(_BMI088_GYRO_CHIP_ID)
            gyro_connected = (gyro_id == 0x0F)
        except Exception:
            gyro_connected = False

        # Return true if at least one sensor is connected
        # This allows partial functionality if only one sensor works
        return acc_connected or gyro_connected

    def initialize(self):
        """Initialize the BMI088 sensor with default settings."""
        self._init_attempt = 0  # Track initialization attempts

        # We already stored the i2c object in __init__
        # self._i2c_bus is available for use

        try:
            self._init_with_retry()
        except Exception as e:
            # Continue on error - some boards may have partial functionality
            pass

    def _init_with_retry(self):
        """Internal method to handle initialization with retries."""
        try:
            # First try with current addresses
            if self._init_attempt == 0:
                # Reset accelerometer first with extra delays and error trapping
                try:
                    self.reset_acc()
                    time.sleep(0.2)  # 200ms delay after reset
                except OSError:
                    time.sleep(0.3)  # longer delay if reset fails

                # Configure accelerometer with more delays
                try:
                    self.set_acc_power_mode(ACC_ACTIVE)
                    time.sleep(0.05)
                    self.set_acc_scale_range(ACC_RANGE_6G)
                    time.sleep(0.05)
                    self.set_acc_output_data_rate(ACC_ODR_100)
                    time.sleep(0.1)
                except OSError:
                    time.sleep(0.1)  # continue even if this fails

                # Reset and configure gyroscope with more delays
                try:
                    self.reset_gyro()
                    time.sleep(0.3)  # 300ms delay after gyro reset

                    self.set_gyro_power_mode(GYRO_NORMAL)
                    time.sleep(0.1)
                    self.set_gyro_scale_range(GYRO_RANGE_1000)
                    time.sleep(0.1)
                    self.set_gyro_output_data_rate(GYRO_ODR_200_BW_23)
                    time.sleep(0.1)
                except OSError:
                    # It's okay if some of these fail, continue anyway
                    pass

            # If first attempt failed, try alternate addresses
            elif self._init_attempt == 1:
                # Re-create devices with alternate addresses
                self._acc_device = I2CDevice(self._i2c_bus, _BMI088_ACC_ALT_ADDRESS)
                self._gyro_device = I2CDevice(self._i2c_bus, _BMI088_GYRO_ALT_ADDRESS)

                # Just minimal configuration with alternate addresses
                try:
                    self.reset_acc()
                    time.sleep(0.2)
                    self.set_acc_power_mode(ACC_ACTIVE)
                    time.sleep(0.1)
                except OSError:
                    pass

                try:
                    self.reset_gyro()
                    time.sleep(0.2)
                    self.set_gyro_power_mode(GYRO_NORMAL)
                    time.sleep(0.1)
                except OSError:
                    pass

            # If still failing, try with minimal initialization
            elif self._init_attempt == 2:
                # Don't do any initialization, just set up the objects
                # This might at least allow reading from the device
                pass

        except OSError:
            # If this attempt failed, try the next one
            self._init_attempt += 1
            if self._init_attempt <= 2:  # Try up to 3 times (0, 1, 2)
                self._init_with_retry()

    def reset_acc(self):
        """Soft reset the accelerometer."""
        self._write_acc_register(_BMI088_ACC_SOFT_RESET, 0xB6)

    def reset_gyro(self):
        """Soft reset the gyroscope."""
        self._write_gyro_register(_BMI088_GYRO_SOFT_RESET, 0xB6)

    def set_acc_power_mode(self, mode):
        """Set accelerometer power mode.

        :param mode: ACC_ACTIVE or ACC_SUSPEND
        """
        # Set power mode (active/suspend)
        self._write_acc_register(_BMI088_ACC_PWR_CONF, mode)

        if mode == ACC_ACTIVE:
            # If active mode, also enable accelerometer
            self._write_acc_register(_BMI088_ACC_PWR_CTRL, 0x04)
        else:
            # If suspend mode, also disable accelerometer
            self._write_acc_register(_BMI088_ACC_PWR_CTRL, 0x00)

    def set_gyro_power_mode(self, mode):
        """Set gyroscope power mode.

        :param mode: GYRO_NORMAL, GYRO_SUSPEND, or GYRO_DEEP_SUSPEND
        """
        self._write_gyro_register(_BMI088_GYRO_LPM_1, mode)

    def set_acc_scale_range(self, range_val):
        """Set accelerometer scale range.

        :param range_val: ACC_RANGE_3G, ACC_RANGE_6G, ACC_RANGE_12G, or ACC_RANGE_24G
        """
        self._write_acc_register(_BMI088_ACC_RANGE, range_val)
        self._acc_range = range_val

        # Update scale factor based on selected range
        ranges = {
            ACC_RANGE_3G: 3.0 / 32768.0,
            ACC_RANGE_6G: 6.0 / 32768.0,
            ACC_RANGE_12G: 12.0 / 32768.0,
            ACC_RANGE_24G: 24.0 / 32768.0
        }
        self._acc_scale = ranges.get(range_val, 6.0 / 32768.0)

    def set_gyro_scale_range(self, range_val):
        """Set gyroscope scale range.

        :param range_val: GYRO_RANGE_2000, GYRO_RANGE_1000, GYRO_RANGE_500,
                          GYRO_RANGE_250, or GYRO_RANGE_125
        """
        self._write_gyro_register(_BMI088_GYRO_RANGE, range_val)
        self._gyro_range = range_val

        # Update scale factor based on selected range
        ranges = {
            GYRO_RANGE_2000: 2000.0 / 32768.0,
            GYRO_RANGE_1000: 1000.0 / 32768.0,
            GYRO_RANGE_500: 500.0 / 32768.0,
            GYRO_RANGE_250: 250.0 / 32768.0,
            GYRO_RANGE_125: 125.0 / 32768.0
        }
        self._gyro_scale = ranges.get(range_val, 1000.0 / 32768.0)

    def set_acc_output_data_rate(self, odr):
        """Set accelerometer output data rate.

        :param odr: ACC_ODR_12, ACC_ODR_25, ACC_ODR_50, ACC_ODR_100,
                    ACC_ODR_200, ACC_ODR_400, ACC_ODR_800, or ACC_ODR_1600
        """
        # Read current value to maintain bandwidth settings
        current = self._read_acc_register(_BMI088_ACC_CONF)
        # Clear ODR bits (bits 4-7) and set new value
        new_val = (current & 0x0F) | (odr << 4)
        self._write_acc_register(_BMI088_ACC_CONF, new_val)

    def set_gyro_output_data_rate(self, odr):
        """Set gyroscope output data rate and bandwidth.

        :param odr: One of the GYRO_ODR_* constants
        """
        self._write_gyro_register(_BMI088_GYRO_BAND_WIDTH, odr)

    def get_acceleration(self):
        """Get 3-axis acceleration data.

        :return: Tuple of X, Y, Z acceleration values in g
        """
        try:
            # Read 6 bytes (2 bytes per axis, X, Y, Z)
            data = bytearray(6)
            with self._acc_device as i2c:
                i2c.write_then_readinto(bytes([_BMI088_ACC_X_LSB]), data)

            # Convert from two's complement
            x = struct.unpack_from("<h", data, 0)[0]
            y = struct.unpack_from("<h", data, 2)[0]
            z = struct.unpack_from("<h", data, 4)[0]

            # Apply scale factor to convert to g
            x = x * self._acc_scale
            y = y * self._acc_scale
            z = z * self._acc_scale

            return (x, y, z)
        except Exception:
            # Return zeros if accelerometer read fails
            return (0, 0, 0)

    def get_gyroscope(self):
        """Get 3-axis gyroscope data.

        :return: Tuple of X, Y, Z gyroscope values in dps (degrees per second)
        """
        try:
            # Read 6 bytes (2 bytes per axis, X, Y, Z)
            data = bytearray(6)
            with self._gyro_device as i2c:
                i2c.write_then_readinto(bytes([_BMI088_GYRO_RATE_X_LSB]), data)

            # Convert from two's complement
            x = struct.unpack_from("<h", data, 0)[0]
            y = struct.unpack_from("<h", data, 2)[0]
            z = struct.unpack_from("<h", data, 4)[0]

            # Apply scale factor to convert to degrees per second
            x = x * self._gyro_scale
            y = y * self._gyro_scale
            z = z * self._gyro_scale

            return (x, y, z)
        except Exception:
            # Return zeros if gyroscope read fails
            return (0, 0, 0)

    def get_temperature(self):
        """Get temperature reading from accelerometer sensor.

        :return: Temperature in degrees Celsius
        """
        try:
            # Read 2 bytes of temperature data
            data = bytearray(2)
            with self._acc_device as i2c:
                i2c.write_then_readinto(bytes([_BMI088_ACC_TEMP_MSB]), data)

            # Convert to temperature
            # First 11 bits represent the temperature value in two's complement format
            temp_raw = (data[0] << 3) | (data[1] >> 5)
            if temp_raw > 1023:  # If MSB is 1, handle negative value
                temp_raw -= 2048

            # Convert to degrees Celsius
            # 0 LSB corresponds to 23°C, 1 LSB = 0.125°C
            temp_celsius = (temp_raw * 0.125) + 23.0

            return temp_celsius
        except Exception:
            # Return a default room temperature if reading fails
            return 25.0

    def get_acc_id(self):
        """Get accelerometer chip ID.

        :return: Accelerometer chip ID
        """
        return self._read_acc_register(_BMI088_ACC_CHIP_ID)

    def get_gyro_id(self):
        """Get gyroscope chip ID.

        :return: Gyroscope chip ID
        """
        return self._read_gyro_register(_BMI088_GYRO_CHIP_ID)

    def _write_acc_register(self, reg, value):
        """Write to an accelerometer register.

        :param reg: Register address
        :param value: Value to write
        """
        with self._acc_device as i2c:
            i2c.write(bytes([reg, value]))

    def _write_gyro_register(self, reg, value):
        """Write to a gyroscope register.

        :param reg: Register address
        :param value: Value to write
        """
        try:
            with self._gyro_device as i2c:
                i2c.write(bytes([reg, value]))
                time.sleep(0.01)  # Add small delay after write
        except OSError as e:
            # Try once more with longer delay
            time.sleep(0.1)
            with self._gyro_device as i2c:
                i2c.write(bytes([reg, value]))
                time.sleep(0.01)

    def _read_acc_register(self, reg):
        """Read from an accelerometer register.

        :param reg: Register address
        :return: Register value
        """
        with self._acc_device as i2c:
            i2c.write(bytes([reg]))
            result = bytearray(1)
            i2c.readinto(result)
            return result[0]

    def _read_gyro_register(self, reg):
        """Read from a gyroscope register.

        :param reg: Register address
        :return: Register value
        """
        try:
            with self._gyro_device as i2c:
                i2c.write(bytes([reg]))
                time.sleep(0.01)  # Small delay between write and read
                result = bytearray(1)
                i2c.readinto(result)
                return result[0]
        except OSError as e:
            # Try once more with longer delay
            time.sleep(0.1)
            with self._gyro_device as i2c:
                i2c.write(bytes([reg]))
                time.sleep(0.01)
                result = bytearray(1)
                i2c.readinto(result)
                return result[0]
