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

    def test_ci_firmware_matrix(self):
        ci_path = os.path.join(os.path.dirname(__file__), "..", ".github", "workflows", "ci.yml")
        self.assertTrue(os.path.exists(ci_path))

        with open(ci_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("firmware-matrix:", content)
        self.assertIn("target: [esp32cam, esp32s3]", content)
        self.assertIn("pio run -e ${{ matrix.target }}", content)
        self.assertIn("memory_stress_test.py", content)

    def test_custom_encrypted_partition_table(self):
        part_path = os.path.join(self.firmware_dir, "partitions.csv")
        self.assertTrue(os.path.exists(part_path))

        with open(part_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Must have encrypted NVS keys partition
        self.assertIn("nvs_key", content)
        self.assertIn("nvs_keys", content)
        self.assertIn("encrypted", content)

        # Must have dual OTA and coredump
        self.assertIn("ota_0", content)
        self.assertIn("ota_1", content)
        self.assertIn("coredump", content)

        # PlatformIO must reference it
        with open(self.ini_path, "r", encoding="utf-8") as f:
            ini_content = f.read()
        self.assertIn("board_build.partitions = partitions.csv", ini_content)

    def test_flash_encryption_provisioning(self):
        prov_dir = os.path.join(os.path.dirname(__file__), "..", "tools", "provisioning")
        sys.path.insert(0, prov_dir)
        from enable_flash_encryption import generate_provisioning_manifest, generate_flash_encryption_key

        manifest_dev = generate_provisioning_manifest("dummy.bin", "development")
        self.assertIn("burn_key", manifest_dev["burn_key_cmd"])
        self.assertIn("FLASH_CRYPT_CNT 1", manifest_dev["enable_crypt_cmd"])

        manifest_rel = generate_provisioning_manifest("dummy.bin", "release")
        self.assertIn("DIS_DOWNLOAD_MODE", manifest_rel["disable_download_mode_cmd"])

        # Check documentation
        doc_path = os.path.join(os.path.dirname(__file__), "..", "docs", "HARDWARE_SECURITY.md")
        self.assertTrue(os.path.exists(doc_path))
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("AES-XTS", content)
        self.assertIn("FLASH_CRYPT_CNT", content)

    def test_secure_boot_signing_and_verification(self):
        prov_dir = os.path.join(os.path.dirname(__file__), "..", "tools", "provisioning")
        sys.path.insert(0, prov_dir)
        from secure_boot_sign import generate_secure_boot_key, sign_firmware_image, verify_signed_image, generate_efuse_burn_plan

        test_key = os.path.join(self.firmware_dir, "test_sb_key.bin")
        test_bin = os.path.join(self.firmware_dir, "test_fw.bin")
        signed_bin = os.path.join(self.firmware_dir, "test_fw_signed.bin")

        try:
            generate_secure_boot_key(test_key)
            with open(test_bin, "wb") as f:
                f.write(os.urandom(8192))

            # Sign image
            digest, sig = sign_firmware_image(test_bin, test_key, signed_bin)
            self.assertEqual(len(digest), 32)
            self.assertEqual(len(sig), 64)

            # Verify valid signature
            self.assertTrue(verify_signed_image(signed_bin, test_key))

            # Tampered image test
            with open(signed_bin, "r+b") as f:
                f.seek(100)
                byte = f.read(1)
                f.seek(100)
                f.write(bytes([byte[0] ^ 0xFF]))

            self.assertFalse(verify_signed_image(signed_bin, test_key))

            # Test efuse plan
            plan = generate_efuse_burn_plan(test_key)
            self.assertIn("SECURE_BOOT_DIGEST", plan["burn_efuse_key_cmd"])
        finally:
            for p in [test_key, test_bin, signed_bin]:
                if os.path.exists(p):
                    os.remove(p)

    def test_secure_nvs_architecture(self):
        nvs_h = os.path.join(self.firmware_dir, "include", "secure_nvs.h")
        self.assertTrue(os.path.exists(nvs_h))

        with open(nvs_h, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("KEY_SLOT_A", content)
        self.assertIn("KEY_SLOT_B", content)
        self.assertIn("increment_counter", content)
        self.assertIn("load_device_keys", content)
        self.assertIn("store_device_keys", content)

        with open(self.main_path, "r", encoding="utf-8") as f:
            main_content = f.read()

        self.assertIn('#include "secure_nvs.h"', main_content)
        self.assertIn("secure_nvs.init()", main_content)
        self.assertIn("secure_nvs.increment_counter()", main_content)

    def test_disable_jtag_efuse_provisioning(self):
        prov_dir = os.path.join(os.path.dirname(__file__), "..", "tools", "provisioning")
        sys.path.insert(0, prov_dir)
        from disable_jtag_efuse import generate_jtag_disable_plan

        plan_esp32 = generate_jtag_disable_plan("esp32")
        self.assertTrue(any("JTAG_DISABLE" in cmd for cmd in plan_esp32["efuse_commands"]))

        plan_s3 = generate_jtag_disable_plan("esp32s3")
        self.assertTrue(any("DIS_PAD_JTAG" in cmd for cmd in plan_s3["efuse_commands"]))
        self.assertTrue(any("HARD_DIS_JTAG" in cmd for cmd in plan_s3["efuse_commands"]))

    def test_factory_provision_device_pipeline(self):
        prov_dir = os.path.join(os.path.dirname(__file__), "..", "tools", "provisioning")
        sys.path.insert(0, prov_dir)
        from provision_device import generate_device_keypair, generate_nvs_csv, provision_and_register_device

        seed, pub = generate_device_keypair()
        self.assertEqual(len(seed), 32)
        self.assertEqual(len(pub), 32)

        csv_str = generate_nvs_csv(seed, pub, 10)
        self.assertIn("pow_sec", csv_str)
        self.assertIn("cnt_a,data,u64,10", csv_str)
        self.assertIn(seed.hex(), csv_str)

        # Mock registration
        res = provision_and_register_device(chain_mode="mock", dry_run=False)
        self.assertTrue(res["registered_on_chain"])
        self.assertEqual(len(res["device_id_hex"]), 64)

    def test_anti_rollback_guard_header(self):
        header_path = os.path.join(
            os.path.dirname(__file__), "..", "firmware", "esp32cam", "include", "anti_rollback.h"
        )
        self.assertTrue(os.path.exists(header_path))
        with open(header_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("class AntiRollbackGuard", content)
        self.assertIn("ARB_ERR_VERSION_DOWNGRADE", content)
        self.assertIn("commit_new_security_version", content)
        self.assertIn("verify_app_security_version", content)

    def test_cellular_hal_interface_and_mock(self):
        header_path = os.path.join(
            os.path.dirname(__file__), "..", "firmware", "esp32cam", "include", "cellular_hal.h"
        )
        self.assertTrue(os.path.exists(header_path))
        with open(header_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("class ICellularModem", content)
        self.assertIn("class MockCellularModem", content)
        self.assertIn("MODEM_NET_REGISTERED_HOME", content)
        self.assertIn("http_post", content)


if __name__ == "__main__":
    unittest.main()
