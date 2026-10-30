#pragma once

/**
 * Proof-of-Weeding Edge Capture Firmware
 * Secure Wear-Leveled NVS Storage & Atomic Monotonic Counter
 *
 * Utilizes the encrypted 'nvs_key' and 'nvs' partitions defined in partitions.csv.
 * Protects Ed25519 private keys from plaintext extraction and prevents replay
 * counter rollback across unexpected power cuts using dual-slot atomic commits.
 */

#include <Arduino.h>
#include <Preferences.h>
#include "nvs_flash.h"
#include "nvs.h"

#define NVS_NAMESPACE "pow_sec"
#define KEY_SLOT_A "cnt_a"
#define KEY_SLOT_B "cnt_b"
#define KEY_PRIV "priv_key"
#define KEY_PUB "pub_key"

class SecureNVS {
private:
    Preferences prefs;
    bool initialized;
    uint64_t current_counter;

public:
    SecureNVS() : initialized(false), current_counter(0) {}

    bool init() {
        // Attempt NVS initialization
        esp_err_t err = nvs_flash_init();
        if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
            Serial.println("[NVS] Truncating/erasing corrupted NVS partition...");
            nvs_flash_erase();
            err = nvs_flash_init();
        }

        if (err != ESP_OK) {
            Serial.printf("[NVS-FATAL] nvs_flash_init failed: 0x%x\n", err);
            return false;
        }

        if (!prefs.begin(NVS_NAMESPACE, false)) {
            Serial.println("[NVS-FATAL] Preferences.begin failed on secure namespace.");
            return false;
        }

        // Recover highest valid monotonic counter across dual slots (atomic commit guard)
        uint64_t cnt_a = prefs.getULong64(KEY_SLOT_A, 0);
        uint64_t cnt_b = prefs.getULong64(KEY_SLOT_B, 0);

        current_counter = (cnt_a > cnt_b) ? cnt_a : cnt_b;
        Serial.printf("[NVS] Secure storage ready. Restored monotonic counter: %llu (Slot A: %llu, Slot B: %llu)\n",
                      current_counter, cnt_a, cnt_b);

        initialized = true;
        return true;
    }

    uint64_t get_counter() const {
        return current_counter;
    }

    uint64_t increment_counter() {
        if (!initialized) return 0;

        current_counter++;
        // Ping-pong atomic commit: write to alternate slot based on parity
        if (current_counter % 2 == 1) {
            prefs.putULong64(KEY_SLOT_A, current_counter);
        } else {
            prefs.putULong64(KEY_SLOT_B, current_counter);
        }

        return current_counter;
    }

    bool has_device_keys() {
        if (!initialized) return false;
        return prefs.isKey(KEY_PRIV) && prefs.isKey(KEY_PUB);
    }

    bool load_device_keys(uint8_t priv_out[32], uint8_t pub_out[32]) {
        if (!has_device_keys()) return false;
        size_t len_sk = prefs.getBytes(KEY_PRIV, priv_out, 32);
        size_t len_pk = prefs.getBytes(KEY_PUB, pub_out, 32);
        return (len_sk == 32 && len_pk == 32);
    }

    bool store_device_keys(const uint8_t priv[32], const uint8_t pub[32]) {
        if (!initialized) return false;
        size_t w_sk = prefs.putBytes(KEY_PRIV, priv, 32);
        size_t w_pk = prefs.putBytes(KEY_PUB, pub, 32);
        return (w_sk == 32 && w_pk == 32);
    }

    void close() {
        if (initialized) {
            prefs.end();
            initialized = false;
        }
    }
};

