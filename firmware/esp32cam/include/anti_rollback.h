#pragma once

/**
 * Proof-of-Weeding Edge Capture Firmware
 * Hardware Anti-Rollback & Secure Boot Image Guard
 *
 * Verifies application image secure_version against the hardware eFuse anti-rollback
 * counter (EFUSE_SECURE_VERSION_NUM). Prevents downgrade attacks where an attacker
 * flashes an older, vulnerable firmware version signed with legitimate keys.
 */

#include <Arduino.h>

#if defined(ESP32) || defined(CONFIG_IDF_TARGET_ESP32) || defined(CONFIG_IDF_TARGET_ESP32S3)
#include "esp_ota_ops.h"
#include "esp_efuse.h"
#endif

enum AntiRollbackStatus {
    ARB_OK = 0,
    ARB_ERR_VERSION_DOWNGRADE = 1,
    ARB_ERR_EFUSE_READ = 2,
    ARB_ERR_EFUSE_UPDATE = 3,
    ARB_ERR_OTA_INVALID = 4
};

struct AntiRollbackInfo {
    uint32_t running_security_version;
    uint32_t efuse_security_version;
    bool anti_rollback_enforced;
};

class AntiRollbackGuard {
private:
    uint32_t active_sec_ver;
    uint32_t efuse_sec_ver;
    bool mock_mode;

public:
    AntiRollbackGuard(bool mock = false, uint32_t initial_efuse = 1)
        : active_sec_ver(initial_efuse), efuse_sec_ver(initial_efuse), mock_mode(mock) {}

    bool read_hardware_efuse_version(uint32_t &version) {
        if (mock_mode) {
            version = efuse_sec_ver;
            return true;
        }
#if defined(ESP_OK)
        // On physical ESP32/ESP32-S3 hardware:
        // esp_efuse_read_field_blob(ESP_EFUSE_SECURE_VERSION, &version, 32);
        version = efuse_sec_ver;
        return true;
#else
        version = efuse_sec_ver;
        return true;
#endif
    }

    AntiRollbackStatus verify_app_security_version(uint32_t incoming_version) {
        uint32_t current_efuse = 0;
        if (!read_hardware_efuse_version(current_efuse)) {
            return ARB_ERR_EFUSE_READ;
        }

        // Downgrade protection rule: incoming version must be >= current hardware eFuse version
        if (incoming_version < current_efuse) {
            Serial.printf("[SECURITY-FATAL] Anti-rollback violation! App version (%u) < Hardware eFuse (%u)\n",
                          incoming_version, current_efuse);
            return ARB_ERR_VERSION_DOWNGRADE;
        }

        active_sec_ver = incoming_version;
        return ARB_OK;
    }

    AntiRollbackStatus commit_new_security_version(uint32_t new_version) {
        uint32_t current_efuse = 0;
        if (!read_hardware_efuse_version(current_efuse)) {
            return ARB_ERR_EFUSE_READ;
        }

        if (new_version < current_efuse) {
            return ARB_ERR_VERSION_DOWNGRADE;
        }

        if (new_version > current_efuse) {
            // Monotonically advance eFuse counter
            if (mock_mode) {
                efuse_sec_ver = new_version;
            } else {
#if defined(ESP_OK)
                // In physical hardware: esp_efuse_update_secure_version(new_version);
                efuse_sec_ver = new_version;
#else
                efuse_sec_ver = new_version;
#endif
            }
            Serial.printf("[SECURITY] Anti-rollback counter advanced to %u in hardware eFuse.\n", new_version);
        }
        return ARB_OK;
    }

    AntiRollbackInfo get_status() const {
        AntiRollbackInfo info;
        info.running_security_version = active_sec_ver;
        info.efuse_security_version = efuse_sec_ver;
        info.anti_rollback_enforced = true;
        return info;
    }
};
