#pragma once

/**
 * Proof-of-Weeding Edge Capture Firmware
 * Power Rail Gating & Peripheral Load Switch Controller
 *
 * Controls high-side PMOS/NMOS load switches for Camera and Cellular Modem rails.
 * Manages power sequencing and prevents parasitic back-powering through I/O pins
 * during deep sleep phases.
 */

#include <Arduino.h>

enum PowerRailTarget {
    RAIL_CAMERA = 0,
    RAIL_CELLULAR_MODEM = 1,
    RAIL_EXTERNAL_FLASH_LED = 2
};

struct RailConfig {
    int control_pin;
    bool active_low;
    uint32_t power_on_delay_ms;
    uint32_t power_off_delay_ms;
};

class PowerRailManager {
private:
    RailConfig cam_rail;
    RailConfig modem_rail;
    bool cam_state;
    bool modem_state;

public:
    PowerRailManager(
        int cam_pin = 32, // Default ESP32-CAM camera power down pin
        bool cam_active_low = true,
        int modem_pin = 4,
        bool modem_active_low = true
    ) : cam_state(false), modem_state(false) {
        cam_rail = {cam_pin, cam_active_low, 25, 10};
        modem_rail = {modem_pin, modem_active_low, 50, 20};
    }

    void init() {
        if (cam_rail.control_pin >= 0) {
            pinMode(cam_rail.control_pin, OUTPUT);
            set_rail(cam_rail, false);
        }
        if (modem_rail.control_pin >= 0) {
            pinMode(modem_rail.control_pin, OUTPUT);
            set_rail(modem_rail, false);
        }
    }

    void set_rail(const RailConfig &cfg, bool enabled) {
        if (cfg.control_pin < 0) return;
        int level;
        if (cfg.active_low) {
            level = enabled ? LOW : HIGH;
        } else {
            level = enabled ? HIGH : LOW;
        }
        digitalWrite(cfg.control_pin, level);
        delay(enabled ? cfg.power_on_delay_ms : cfg.power_off_delay_ms);
    }

    bool power_camera(bool on) {
        set_rail(cam_rail, on);
        cam_state = on;
        Serial.printf("[POWER-RAIL] Camera rail %s\n", on ? "ENABLED" : "ISOLATED");
        return true;
    }

    bool power_modem(bool on) {
        set_rail(modem_rail, on);
        modem_state = on;
        Serial.printf("[POWER-RAIL] Cellular modem rail %s\n", on ? "ENABLED" : "ISOLATED");
        return true;
    }

    void isolate_all_for_sleep() {
        power_camera(false);
        power_modem(false);
        Serial.println("[POWER-RAIL] All peripheral power rails isolated for deep-sleep.");
    }

    bool is_camera_powered() const { return cam_state; }
    bool is_modem_powered() const { return modem_state; }
};

