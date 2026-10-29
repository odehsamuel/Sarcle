#pragma once

/**
 * Proof-of-Weeding Edge Capture Firmware
 * Dynamic Network Failover Engine (Cellular Primary, Wi-Fi Fallback)
 *
 * Orchestrates physical telemetry uplink. Attempts cellular LTE-M/NB-IoT uplink first,
 * falling back to local 802.11 Wi-Fi if cellular registration fails or RSSI is inadequate.
 */

#include <Arduino.h>
#include "cellular_hal.h"

#if defined(ESP32)
#include <WiFi.h>
#include <HTTPClient.h>
#endif

enum NetworkRoute {
    ROUTE_NONE = 0,
    ROUTE_CELLULAR = 1,
    ROUTE_WIFI = 2
};

struct NetworkStatusInfo {
    NetworkRoute active_route;
    bool is_connected;
    int signal_strength_dbm;
    uint32_t failover_count;
};

class NetworkManager {
private:
    ICellularModem *modem;
    const char *wifi_ssid;
    const char *wifi_pass;
    const char *target_url;
    NetworkRoute current_route;
    uint32_t failover_counter;

public:
    NetworkManager(
        ICellularModem *cell_modem,
        const char *ssid = nullptr,
        const char *pass = nullptr,
        const char *endpoint_url = "https://attester.proofofweeding.org/api/observations"
    ) : modem(cell_modem),
        wifi_ssid(ssid),
        wifi_pass(pass),
        target_url(endpoint_url),
        current_route(ROUTE_NONE),
        failover_counter(0) {}

    bool connect_cellular() {
        if (!modem) return false;

        if (!modem->power_on()) return false;
        delay(1000);

        SignalMetrics sig = modem->get_signal_metrics();
        if (sig.rssi_dbm < -110) {
            Serial.printf("[NET] Cellular signal too weak (%d dBm)\n", sig.rssi_dbm);
            return false;
        }

        if (!modem->configure_apn("")) return false;
        if (!modem->activate_pdp_context()) return false;

        current_route = ROUTE_CELLULAR;
        Serial.println("[NET] Connected via Cellular LTE-M uplink.");
        return true;
    }

    bool connect_wifi() {
        if (!wifi_ssid || strlen(wifi_ssid) == 0) return false;

#if defined(ESP32)
        Serial.printf("[NET] Attempting Wi-Fi fallback to SSID: %s\n", wifi_ssid);
        WiFi.mode(WIFI_STA);
        WiFi.begin(wifi_ssid, wifi_pass);

        uint32_t start = millis();
        while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) {
            delay(250);
        }

        if (WiFi.status() == WL_CONNECTED) {
            current_route = ROUTE_WIFI;
            failover_counter++;
            Serial.println("[NET] Connected via Wi-Fi fallback.");
            return true;
        }
#endif
        return false;
    }

    bool ensure_connectivity() {
        // Step 1: Attempt cellular primary
        if (connect_cellular()) {
            return true;
        }

        Serial.println("[NET] Cellular connection failed. Triggering failover to Wi-Fi...");
        // Step 2: Attempt Wi-Fi fallback
        if (connect_wifi()) {
            return true;
        }

        current_route = ROUTE_NONE;
        return false;
    }

    int post_payload(
        const uint8_t *data,
        size_t len,
        char *resp_buf = nullptr,
        size_t resp_buf_max = 0
    ) {
        if (current_route == ROUTE_NONE) {
            if (!ensure_connectivity()) {
                return -1;
            }
        }

        if (current_route == ROUTE_CELLULAR && modem) {
            int code = modem->http_post(target_url, data, len, "application/octet-stream", resp_buf, resp_buf_max);
            if (code > 0) return code;

            // Cellular post failed in-flight, try Wi-Fi fallback
            Serial.println("[NET] Cellular post failed; falling back to Wi-Fi...");
            if (connect_wifi()) {
                // Proceed with Wi-Fi below
            } else {
                return code;
            }
        }

        if (current_route == ROUTE_WIFI) {
#if defined(ESP32)
            HTTPClient http;
            http.begin(target_url);
            http.addHeader("Content-Type", "application/octet-stream");
            int http_code = http.POST((uint8_t *)data, len);
            if (http_code > 0 && resp_buf && resp_buf_max > 0) {
                String payload = http.getString();
                strncpy(resp_buf, payload.c_str(), resp_buf_max - 1);
                resp_buf[resp_buf_max - 1] = '\0';
            }
            http.end();
            return http_code;
#else
            return 200;
#endif
        }

        return -1;
    }

    void disconnect_all() {
        if (modem) {
            modem->deactivate_pdp_context();
            modem->power_off();
        }
#if defined(ESP32)
        if (WiFi.status() == WL_CONNECTED) {
            WiFi.disconnect(true);
        }
#endif
        current_route = ROUTE_NONE;
    }

    NetworkStatusInfo get_status() {
        NetworkStatusInfo info;
        info.active_route = current_route;
        info.is_connected = (current_route != ROUTE_NONE);
        info.failover_count = failover_counter;
        if (current_route == ROUTE_CELLULAR && modem) {
            info.signal_strength_dbm = modem->get_signal_metrics().rssi_dbm;
        } else {
            info.signal_strength_dbm = -60;
        }
        return info;
    }
};
