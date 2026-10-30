#pragma once

/**
 * Proof-of-Weeding Edge Capture Firmware
 * UART Diagnostic Shell & Field Commissioning CLI
 * Provides non-blocking interactive health checks over UART0 (115200 baud).
 */

#include <Arduino.h>
#include <Preferences.h>
#include "board_pins.h"
#include "camera_hal.h"
#include "psram_allocator.h"
#include "crypto_benchmark.h"

class DiagnosticCLI {
private:
    char input_buffer[64];
    size_t input_len;

    void print_hex(const char* label, const uint8_t* data, size_t len) {
        Serial.print(label);
        for (size_t i = 0; i < len; i++) {
            if (data[i] < 0x10) Serial.print("0");
            Serial.print(data[i], HEX);
        }
        Serial.println();
    }

public:
    DiagnosticCLI() : input_len(0) {
        memset(input_buffer, 0, sizeof(input_buffer));
    }

    void print_prompt() {
        Serial.print("\nPoW-Edge> ");
    }

    void print_help() {
        Serial.println("\n--- Proof-of-Weeding Diagnostic CLI ---");
        Serial.println("  help    : Display this menu");
        Serial.println("  info    : Show board, chip, CPU, and firmware telemetry");
        Serial.println("  cam     : Perform live camera capture test & validate frame size");
        Serial.println("  mem     : Report internal SRAM and external PSRAM heap usage");
        Serial.println("  bench   : Run cryptographic benchmark (SHA-256 and Ed25519)");
        Serial.println("  nvs     : Display device public key and monotonic counter");
        Serial.println("  reboot  : Restart microcontroller");
        Serial.println("----------------------------------------");
    }

    void handle_command(const char* cmd, CameraHAL& camera, Preferences& prefs, const uint8_t* pk, uint64_t counter) {
        if (strcmp(cmd, "help") == 0 || strcmp(cmd, "?") == 0) {
            print_help();
        } else if (strcmp(cmd, "info") == 0) {
            Serial.println("\n[INFO] Device Hardware & Platform Telemetry:");
            Serial.printf("  Target Platform:   %s\n", BOARD_NAME);
            Serial.printf("  Chip Model:        %s (Rev %u, %u Cores)\n", ESP.getChipModel(), ESP.getChipRevision(), ESP.getChipCores());
            Serial.printf("  CPU Frequency:     %u MHz\n", getCpuFrequencyMhz());
            Serial.printf("  SDK Version:       %s\n", ESP.getSdkVersion());
            Serial.printf("  Uptime:            %lu ms\n", millis());
        } else if (strcmp(cmd, "cam") == 0) {
            Serial.println("\n[CAM] Executing diagnostic camera capture...");
            CameraCaptureResult res = camera.capture();
            if (res.success) {
                Serial.printf("  [PASS] Frame captured: %zu bytes (Sensor: %s)\n", res.length, camera.get_sensor_name());
                camera.release(res.fb);
            } else {
                Serial.printf("  [FAIL] Capture failed: %s\n", res.error_msg);
            }
        } else if (strcmp(cmd, "mem") == 0) {
            PsramAllocator::print_memory_stats();
        } else if (strcmp(cmd, "bench") == 0) {
            CryptoBenchmark::run(10);
        } else if (strcmp(cmd, "nvs") == 0) {
            Serial.println("\n[NVS] Cryptographic State & Storage:");
            print_hex("  Device Public Key (Ed25519): ", pk, 32);
            Serial.printf("  Monotonic Replay Counter:    %llu\n", counter);
        } else if (strcmp(cmd, "reboot") == 0) {
            Serial.println("[SYS] Rebooting device...");
            delay(200);
            ESP.restart();
        } else if (strlen(cmd) > 0) {
            Serial.printf("[ERR] Unknown command: '%s'. Type 'help' for available commands.\n", cmd);
        }
        print_prompt();
    }

    void process_serial(CameraHAL& camera, Preferences& prefs, const uint8_t* pk, uint64_t counter) {
        while (Serial.available() > 0) {
            char c = (char)Serial.read();
            if (c == '\r' || c == '\n') {
                if (input_len > 0) {
                    input_buffer[input_len] = '\0';
                    handle_command(input_buffer, camera, prefs, pk, counter);
                    input_len = 0;
                }
            } else if (c == '\b' || c == 127) { // Backspace
                if (input_len > 0) {
                    input_len--;
                    Serial.print("\b \b");
                }
            } else if (input_len < sizeof(input_buffer) - 1) {
                input_buffer[input_len++] = c;
                Serial.print(c); // Echo character
            }
        }
    }
};
