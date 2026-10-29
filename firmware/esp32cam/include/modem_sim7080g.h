#pragma once

/**
 * Proof-of-Weeding Edge Capture Firmware
 * SIMCom SIM7080G Driver & Global IoT APN Auto-Negotiation
 *
 * Implements ICellularModem for SIMCom SIM7080G (Cat-M / NB-IoT).
 * Includes auto-discovery table for international SIM profiles (Hologram, Soracom, 1NCE, EMnify).
 */

#include "cellular_hal.h"

struct ApnProfile {
    const char *imsi_prefix; // 5-digit MCC+MNC or empty for default
    const char *apn;
    const char *username;
    const char *password;
};

static const ApnProfile KNOWN_APN_PROFILES[] = {
    {"44010", "soracom.io", "sora", "sora"},      // Soracom Japan/Global
    {"20404", "iot.1nce.net", "", ""},             // 1NCE Germany/Global
    {"29505", "em", "", ""},                       // EMnify
    {"31026", "super", "", ""},                    // Twilio Super SIM
    {"", "hologram", "", ""}                       // Hologram Global Default Fallback
};

class SIM7080GModem : public ICellularModem {
private:
    Stream *serial;
    int pin_pwrkey;
    int pin_reset;
    bool powered;
    bool pdp_active;
    String active_apn;

public:
    SIM7080GModem(Stream *serial_port, int pwrkey_pin = -1, int reset_pin = -1)
        : serial(serial_port),
          pin_pwrkey(pwrkey_pin),
          pin_reset(reset_pin),
          powered(false),
          pdp_active(false),
          active_apn("hologram") {}

    bool power_on() override {
        if (pin_pwrkey >= 0) {
            pinMode(pin_pwrkey, OUTPUT);
            digitalWrite(pin_pwrkey, LOW);
            delay(100);
            digitalWrite(pin_pwrkey, HIGH);
            delay(1200); // SIM7080G PWRKEY > 1000ms
            digitalWrite(pin_pwrkey, LOW);
            delay(3000);
        }
        powered = true;

        for (int i = 0; i < 5; ++i) {
            if (send_at_command("AT", "OK", 500)) break;
            delay(200);
        }
        send_at_command("ATE0", "OK", 500);
        return true;
    }

    bool power_off() override {
        if (pdp_active) deactivate_pdp_context();
        send_at_command("AT+CPOWD=1", "NORMAL POWER DOWN", 2000);
        powered = false;
        return true;
    }

    bool reset() override {
        if (pin_reset >= 0) {
            pinMode(pin_reset, OUTPUT);
            digitalWrite(pin_reset, HIGH);
            delay(200);
            digitalWrite(pin_reset, LOW);
            delay(2500);
        } else {
            send_at_command("AT+AT+CFUN=1,1", "OK", 3000);
        }
        powered = true;
        pdp_active = false;
        return true;
    }

    bool send_at_command(
        const char *command,
        const char *expected_response,
        uint32_t timeout_ms,
        char *response_buffer = nullptr,
        size_t buffer_size = 0
    ) override {
        if (!serial) return false;

        while (serial->available()) serial->read();
        serial->print(command);
        serial->print("\r\n");

        uint32_t start_ms = millis();
        size_t idx = 0;

        while (millis() - start_ms < timeout_ms) {
            while (serial->available()) {
                char c = serial->read();
                if (response_buffer && idx < buffer_size - 1) {
                    response_buffer[idx++] = c;
                    response_buffer[idx] = '\0';
                }
            }

            if (response_buffer && expected_response && strstr(response_buffer, expected_response) != nullptr) {
                return true;
            }
            if (response_buffer && strstr(response_buffer, "ERROR") != nullptr) {
                return false;
            }
            delay(10);
        }
        return false;
    }

    SignalMetrics get_signal_metrics() override {
        SignalMetrics metrics = {-113, 99, -140, -20, false};
        char buf[128] = {0};
        if (send_at_command("AT+CSQ", "+CSQ:", 1000, buf, sizeof(buf))) {
            char *p = strstr(buf, "+CSQ:");
            if (p) {
                int raw_csq = 99, raw_ber = 99;
                if (sscanf(p, "+CSQ: %d,%d", &raw_csq, &raw_ber) >= 1) {
                    if (raw_csq <= 31) {
                        metrics.rssi_dbm = -113 + 2 * raw_csq;
                        metrics.signal_ok = true;
                    }
                    metrics.ber = raw_ber;
                }
            }
        }
        return metrics;
    }

    ModemNetworkStatus get_network_status() override {
        char buf[128] = {0};
        if (!send_at_command("AT+CGREG?", "+CGREG:", 1000, buf, sizeof(buf))) {
            return MODEM_NET_ERROR;
        }

        char *p = strstr(buf, "+CGREG:");
        if (!p) return MODEM_NET_ERROR;

        int n = 0, stat = 0;
        if (sscanf(p, "+CGREG: %d,%d", &n, &stat) == 2 || sscanf(p, "+CGREG: %d", &stat) == 1) {
            switch (stat) {
                case 1: return MODEM_NET_REGISTERED_HOME;
                case 2: return MODEM_NET_SEARCHING;
                case 3: return MODEM_NET_DENIED;
                case 5: return MODEM_NET_REGISTERED_ROAMING;
                default: return MODEM_NET_DISCONNECTED;
            }
        }
        return MODEM_NET_ERROR;
    }

    String auto_detect_apn() {
        char buf[64] = {0};
        if (send_at_command("AT+CIMI", "OK", 2000, buf, sizeof(buf))) {
            for (size_t i = 0; i < sizeof(KNOWN_APN_PROFILES) / sizeof(KNOWN_APN_PROFILES[0]); ++i) {
                if (strlen(KNOWN_APN_PROFILES[i].imsi_prefix) > 0 &&
                    strstr(buf, KNOWN_APN_PROFILES[i].imsi_prefix) != nullptr) {
                    return String(KNOWN_APN_PROFILES[i].apn);
                }
            }
        }
        // Fallback default
        return String("hologram");
    }

    bool configure_apn(const char *apn) override {
        active_apn = (apn && strlen(apn) > 0) ? String(apn) : auto_detect_apn();
        char cmd[128];
        snprintf(cmd, sizeof(cmd), "AT+CNACT=0,1,\"%s\"", active_apn.c_str());
        return send_at_command(cmd, "OK", 3000);
    }

    bool activate_pdp_context() override {
        if (pdp_active) return true;
        char buf[128] = {0};
        if (send_at_command("AT+CNACT=0,1", "ACTIVE", 30000, buf, sizeof(buf))) {
            pdp_active = true;
            return true;
        }
        return false;
    }

    bool deactivate_pdp_context() override {
        if (!pdp_active) return true;
        if (send_at_command("AT+CNACT=0,0", "OK", 5000)) {
            pdp_active = false;
            return true;
        }
        return false;
    }

    int http_post(
        const char *url,
        const uint8_t *data,
        size_t data_len,
        const char *content_type,
        char *response_buf,
        size_t response_buf_max
    ) override {
        (void)content_type;
        if (!pdp_active && !activate_pdp_context()) return -1;

        // Configure SIM7080G HTTP(S) stack
        char conf_url[128];
        snprintf(conf_url, sizeof(conf_url), "AT+SHCONF=\"URL\",\"%s\"", url);
        send_at_command(conf_url, "OK", 1000);
        send_at_command("AT+SHCONF=\"BODYLEN\",1024", "OK", 1000);
        send_at_command("AT+SHCONF=\"HEADERLEN\",350", "OK", 1000);

        if (!send_at_command("AT+SHCONN", "OK", 15000)) {
            return -2;
        }

        char bod_cmd[64];
        snprintf(bod_cmd, sizeof(bod_cmd), "AT+SHBOD=%u,10000", (unsigned int)data_len);
        if (!send_at_command(bod_cmd, ">", 5000)) {
            send_at_command("AT+SHDISC", "OK", 2000);
            return -3;
        }
        serial->write(data, data_len);
        delay(200);

        char req_resp[128] = {0};
        // Request POST = 3
        if (!send_at_command("AT+SHREQ=\"/api/observations\",3", "+SHREQ:", 30000, req_resp, sizeof(req_resp))) {
            send_at_command("AT+SHDISC", "OK", 2000);
            return -4;
        }

        int status = 0, len = 0;
        char *p = strstr(req_resp, "+SHREQ:");
        if (p && sscanf(p, "+SHREQ: \"POST\",%d,%d", &status, &len) >= 1) {
            if (response_buf && response_buf_max > 0 && len > 0) {
                char read_cmd[64];
                snprintf(read_cmd, sizeof(read_cmd), "AT+SHREAD=0,%d", len);
                send_at_command(read_cmd, "+SHREAD:", 5000, response_buf, response_buf_max);
            }
            send_at_command("AT+SHDISC", "OK", 2000);
            return status;
        }

        send_at_command("AT+SHDISC", "OK", 2000);
        return -5;
    }
};
