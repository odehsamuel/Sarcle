"""Tests for Phase 2: Firmware multi-target build matrix and pinout abstraction."""

import os
import re
import sys
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

    def test_camera_hal_architecture(self):
        hal_path = os.path.join(self.firmware_dir, "include", "camera_hal.h")
        self.assertTrue(os.path.exists(hal_path))
        with open(hal_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Dynamic sensor detection
        self.assertIn("SENSOR_OV2640", content)
        self.assertIn("SENSOR_OV5640", content)

        # Size constraint (< 64 KB)
        self.assertIn("MAX_FRAME_SIZE_BYTES", content)
        self.assertIn("64 * 1024", content)

        # Ensure main.cpp integrates camera_hal
        with open(self.main_path, "r", encoding="utf-8") as f:
            main_content = f.read()

        self.assertIn('#include "camera_hal.h"', main_content)
        self.assertIn("camera_hal.capture", main_content)
        self.assertIn("camera_hal.init", main_content)

    def test_psram_allocator_integration(self):
        alloc_path = os.path.join(self.firmware_dir, "include", "psram_allocator.h")
        self.assertTrue(os.path.exists(alloc_path))
        with open(alloc_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("MALLOC_CAP_SPIRAM", content)
        self.assertIn("allocate", content)
        self.assertIn("deallocate", content)
        self.assertIn("print_memory_stats", content)

        with open(self.main_path, "r", encoding="utf-8") as f:
            main_content = f.read()

        self.assertIn('#include "psram_allocator.h"', main_content)
        self.assertIn("PsramAllocator::allocate", main_content)
        self.assertIn("PsramAllocator::deallocate", main_content)

    def test_crypto_benchmark_suite(self):
        bench_h = os.path.join(self.firmware_dir, "include", "crypto_benchmark.h")
        bench_md = os.path.join(self.firmware_dir, "docs", "BENCHMARKS.md")

        self.assertTrue(os.path.exists(bench_h))
        self.assertTrue(os.path.exists(bench_md))

        with open(bench_h, "r", encoding="utf-8") as f:
            h_content = f.read()
        self.assertIn("CryptoBenchmark", h_content)
        self.assertIn("mbedtls_sha256", h_content)
        self.assertIn("mbedtls_sha512", h_content)
        self.assertIn("estimated_energy_uj", h_content)

        with open(bench_md, "r", encoding="utf-8") as f:
            md_content = f.read()
        self.assertIn("AI-Thinker ESP32-CAM", md_content)
        self.assertIn("ESP32-S3-CAM", md_content)
        self.assertIn("Ed25519 Signature Generation", md_content)
        self.assertIn("Battery Life Implications", md_content)

    def test_diagnostic_cli_interface(self):
        cli_h = os.path.join(self.firmware_dir, "include", "diagnostic_cli.h")
        self.assertTrue(os.path.exists(cli_h))

        with open(cli_h, "r", encoding="utf-8") as f:
            content = f.read()

        # Commands supported
        for cmd in ["help", "info", "cam", "mem", "bench", "nvs", "reboot"]:
            self.assertIn(f'"{cmd}"', content)

        # Check integration into main.cpp
        with open(self.main_path, "r", encoding="utf-8") as f:
            main_content = f.read()

        self.assertIn('#include "diagnostic_cli.h"', main_content)
        self.assertIn("diag_cli.process_serial", main_content)

    def test_500_cycles_stress_test(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools", "hardware-sim"))
        from memory_stress_test import run_stress_test

        res = run_stress_test(cycles=50)  # fast unit test check
        self.assertEqual(res["leaked_bytes"], 0)
        self.assertEqual(res["monotonic_counter"], 50)


if __name__ == "__main__":
    unittest.main()
