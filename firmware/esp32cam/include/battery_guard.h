#pragma once

/**
 * Proof-of-Weeding Edge Capture Firmware
 * Battery Telemetry & Brownout Safety Cutoff Guard
 *
 * Samples LiPo/18650 cell voltage via calibrated ADC divider.
 * Enforces hardware abort threshold (< 3.3V) to prevent flash corruption,
 * brownout loops, and catastrophic battery over-discharge.
 */

#include <Arduino.h>

#if defined(ESP32)
#include "esp_adc_cal.h"
#endif

enum BatteryHealthState {
    BATTERY_HEALTHY = 0,      // > 3.6V: Full operation permitted
    BATTERY_LOW_WARNING = 1,  // 3.3V - 3.6V: Non-essential peripherals (LED flash) disabled
    BATTERY_CRITICAL_ABORT = 2 // < 3.3V: Operation aborted, enter emergency deep-sleep
};

struct BatteryStatus {
    uint32_t voltage_mv;
    BatteryHealthState state;
    uint8_t state_of_charge_percent;
    bool safe_to_operate;
};

class BatteryGuard {
private:
    int adc_pin;
    float divider_ratio;       // (R1 + R2) / R2
    uint32_t warning_mv;
    uint32_t critical_abort_mv;
    bool mock_mode;
    uint32_t mock_voltage_mv;

public:
    BatteryGuard(
        int pin = 33,
        float divider = 2.0f, // Equal 100k/100k resistors -> 2:1 ratio
        uint32_t warn_mv = 3500,
        uint32_t abort_mv = 3300,
        bool mock = false
    ) : adc_pin(pin),
        divider_ratio(divider),
        warning_mv(warn_mv),
        critical_abort_mv(abort_mv),
        mock_mode(mock),
        mock_voltage_mv(3900) {}

    void set_mock_voltage(uint32_t mv) {
        mock_mode = true;
        mock_voltage_mv = mv;
    }

    uint32_t read_voltage_mv() {
        if (mock_mode) {
            return mock_voltage_mv;
        }

#if defined(ESP32)
        uint32_t raw_adc = analogRead(adc_pin);
        // ESP32 default 12-bit ADC, 3.3V ref (~0.8mV/step)
        float pin_voltage = (raw_adc / 4095.0f) * 3300.0f;
        return (uint32_t)(pin_voltage * divider_ratio);
#else
        return mock_voltage_mv;
#endif
    }

    uint8_t estimate_soc_percent(uint32_t mv) {
        // Linear approximation for 3.3V (0%) to 4.2V (100%)
        if (mv <= 3300) return 0;
        if (mv >= 4200) return 100;
        return (uint8_t)(((mv - 3300) * 100) / (4200 - 3300));
    }

    BatteryStatus evaluate_safety() {
        uint32_t mv = read_voltage_mv();
        BatteryStatus status;
        status.voltage_mv = mv;
        status.state_of_charge_percent = estimate_soc_percent(mv);

        if (mv < critical_abort_mv) {
            status.state = BATTERY_CRITICAL_ABORT;
            status.safe_to_operate = false;
            Serial.printf("[BATTERY-FATAL] Voltage %u mV < %u mV! Aborting capture to prevent brownout.\n",
                          mv, critical_abort_mv);
        } else if (mv < warning_mv) {
            status.state = BATTERY_LOW_WARNING;
            status.safe_to_operate = true;
            Serial.printf("[BATTERY-WARN] Voltage %u mV low. Auxiliary LED flash disabled.\n", mv);
        } else {
            status.state = BATTERY_HEALTHY;
            status.safe_to_operate = true;
        }

        return status;
    }

    bool is_safe_to_operate() {
        return evaluate_safety().safe_to_operate;
    }
};

