"""Tests for Phase 2: Firmware multi-target build matrix and pinout abstraction."""

import os
import re
import unittest


class TestFirmwareConfiguration(unittest.TestCase):
    def setUp(self):
        self.firmware_dir = os.path.join(
            os.path.dirname(__file__), "..", "firmware", "esp32cam"
        )
        self.ini_path = os.path.join(self.firmware_dir, "platformio.ini")
        self.pins_path = os.path.join(self.firmware_dir, "include", "board_pins.h")
        self.main_path = os.path.join(self.firmware_dir, "src", "main.cpp")

    def test_platformio_ini_multi_targets(self):
        self.assertTrue(os.path.exists(self.ini_path))
        with open(self.ini_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Both environments must be defined
        self.assertIn("[env:esp32cam]", content)
        self.assertIn("[env:esp32s3]", content)

        # Check target build flags
        self.assertIn("-DTARGET_ESP32_CAM", content)
        self.assertIn("-DTARGET_ESP32_S3", content)
        self.assertIn("-DBOARD_HAS_PSRAM", content)

    def test_board_pins_header_definitions(self):
        self.assertTrue(os.path.exists(self.pins_path))
        with open(self.pins_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check macro guards
        self.assertIn("#if defined(TARGET_ESP32_S3)", content)
        self.assertIn("TARGET_ESP32_CAM", content)

        # Required pin names for both platforms
        required_pins = [
            "PWDN_GPIO_NUM",
            "RESET_GPIO_NUM",
            "XCLK_GPIO_NUM",
            "SIOD_GPIO_NUM",
            "SIOC_GPIO_NUM",
            "Y9_GPIO_NUM",
            "Y2_GPIO_NUM",
            "VSYNC_GPIO_NUM",
            "HREF_GPIO_NUM",
            "PCLK_GPIO_NUM",
            "STATUS_LED_PIN",
        ]
        for pin in required_pins:
            self.assertIn(pin, content, f"Missing pin definition: {pin}")

    def test_main_cpp_uses_board_pins(self):
        with open(self.main_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn('#include "board_pins.h"', content)
        self.assertIn("BOARD_NAME", content)
        self.assertIn("STATUS_LED_PIN", content)


if __name__ == "__main__":
    unittest.main()
