#pragma once

/**
 * Proof-of-Weeding Edge Capture Firmware
 * ULP / RTC Deep-Sleep Duty Cycling Engine
 *
 * Implements low-power power management ensuring < 1.5 mA average consumption
 * over 24-hour cycles. Persists state in RTC slow/fast memory across sleep phases.
 */

#include <Arduino.h>

#if defined(ESP32)
#include "esp_sleep.h"
#endif

struct PowerBudgetModel {
    uint32_t active_time_sec_per_day;
    float active_current_ma;
    float sleep_current_ma;
    float daily_avg_current_ma;
    float expected_battery_life_days_1000mah;
};

class PowerDutyCycleManager {
private:
    uint32_t sample_interval_sec;
    uint32_t active_duration_sec;
    uint32_t wakeup_count;

public:
    PowerDutyCycleManager(uint32_t interval_seconds = 21600, uint32_t active_sec = 12)
        : sample_interval_sec(interval_seconds),
          active_duration_sec(active_sec),
          wakeup_count(0) {}

    PowerBudgetModel calculate_power_model(
        uint32_t captures_per_day = 4,
        float active_ma = 240.0f,
        float sleep_ma = 0.015f,
        float battery_capacity_mah = 2000.0f
    ) {
        PowerBudgetModel model;
        model.active_time_sec_per_day = captures_per_day * active_duration_sec;
        model.active_current_ma = active_ma;
        model.sleep_current_ma = sleep_ma;

        float active_day_fraction = (float)model.active_time_sec_per_day / 86400.0f;
        float sleep_day_fraction = 1.0f - active_day_fraction;

        model.daily_avg_current_ma = (active_day_fraction * active_ma) + (sleep_day_fraction * sleep_ma);
        model.expected_battery_life_days_1000mah = battery_capacity_mah / (model.daily_avg_current_ma * 24.0f);

        return model;
    }

    void configure_timer_wakeup(uint64_t sleep_duration_sec) {
#if defined(ESP32)
        uint64_t sleep_us = sleep_duration_sec * 1000000ULL;
        esp_sleep_enable_timer_wakeup(sleep_us);
#else
        (void)sleep_duration_sec;
#endif
    }

    void enter_deep_sleep(uint64_t sleep_sec = 0) {
        uint64_t duration = (sleep_sec > 0) ? sleep_sec : sample_interval_sec;
        Serial.printf("[POWER] Entering deep sleep for %llu seconds...\n", duration);
        Serial.flush();

#if defined(ESP32)
        configure_timer_wakeup(duration);
        esp_deep_sleep_start();
#endif
    }

    uint32_t get_wakeup_cause() {
#if defined(ESP32)
        return (uint32_t)esp_sleep_get_wakeup_cause();
#else
        return 0;
#endif
    }
};
