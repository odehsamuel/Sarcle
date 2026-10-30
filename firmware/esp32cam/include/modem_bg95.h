#pragma once

/**
 * Proof-of-Weeding Edge Capture Firmware
 * Quectel BG95 Driver (LTE-M / NB-IoT / EGPRS)
 *
 * Implements ICellularModem using Quectel BG95 AT command set.
 * Supports hardware powerkey toggling, context configuration (QICSGP),
 * network registration polling (CEREG/QNWINFO), and embedded HTTP POST (QHTTPPOST).
 */

#include "cellular_hal.h"

class QuectelBG95Modem : public ICellularModem {
private:
    Stream *serial;
    int pin_pwrkey;
    int pin_reset;
    bool powered;
    bool pdp_active;
    String apn_name;

public:
    QuectelBG95Modem(Stream *serial_port, int pwrkey_pin = -1, int reset_pin = -1)
        : serial(serial_port),
          pin_pwrkey(pwrkey_pin),
          pin_reset(reset_pin),
          powered(false),
          pdp_active(false),
          apn_name("hologram") {}

    bool power_on() override {
        if (pin_pwrkey >= 0) {
            pinMode(pin_pwrkey, OUTPUT);
            digitalWrite(pin_pwrkey, LOW);
            delay(100);
            digitalWrite(pin_pwrkey, HIGH);
            delay(500); // BG95 PWRKEY active pulse > 500ms
            digitalWrite(pin_pwrkey, LOW);
            delay(2000); // Wait for module boot
        }
        powered = true;

        // Synchronize baud rate with autobauding
        for (int i = 0; i < 5; ++i) {
            if (send_at_command("AT", "OK", 500)) {
                break;
            }
            delay(200);
        }

        // Disable echo
        send_at_command("ATE0", "OK", 500);
        return true;
    }

    bool power_off() override {
        if (pdp_active) {
            deactivate_pdp_context();
        }
        send_at_command("AT+QPOWD=1", "POWERED DOWN", 2000);
        powered = false;
        return true;
    }

    bool reset() override {
        if (pin_reset >= 0) {
            pinMode(pin_reset, OUTPUT);
            digitalWrite(pin_reset, HIGH);
            delay(150); // BG95 RESET active pulse 150-460ms
            digitalWrite(pin_reset, LOW);
            delay(2000);
        } else {
            send_at_command("AT+CFUN=1,1", "OK", 3000);
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

        // Clear RX FIFO
        while (serial->available()) {
            serial->read();
        }

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
                int raw_csq = 99;
                int raw_ber = 99;
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
        if (!send_at_command("AT+CEREG?", "+CEREG:", 1000, buf, sizeof(buf))) {
            return MODEM_NET_ERROR;
        }

        char *p = strstr(buf, "+CEREG:");
        if (!p) return MODEM_NET_ERROR;

        int n = 0, stat = 0;
        if (sscanf(p, "+CEREG: %d,%d", &n, &stat) == 2 || sscanf(p, "+CEREG: %d", &stat) == 1) {
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

    bool configure_apn(const char *apn) override {
        apn_name = apn;
        char cmd[128];
        snprintf(cmd, sizeof(cmd), "AT+QICSGP=1,1,\"%s\",\"\",\"\",1", apn);
        return send_at_command(cmd, "OK", 2000);
    }

    bool activate_pdp_context() override {
        if (pdp_active) return true;
        if (send_at_command("AT+QIACT=1", "OK", 30000)) {
            pdp_active = true;
            return true;
        }
        return false;
    }

    bool deactivate_pdp_context() override {
        if (!pdp_active) return true;
        if (send_at_command("AT+QIDEACT=1", "OK", 10000)) {
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
        if (!pdp_active) {
            if (!activate_pdp_context()) return -1;
        }

        // Configure HTTP context
        send_at_command("AT+QHTTPCFG=\"contextid\",1", "OK", 1000);
        send_at_command("AT+QHTTPCFG=\"responseheader\",1", "OK", 1000);

        char header_cmd[128];
        snprintf(header_cmd, sizeof(header_cmd), "AT+QHTTPCFG=\"customheader\",\"Content-Type: %s\"", content_type);
        send_at_command(header_cmd, "OK", 1000);

        // Send URL
        char url_cmd[64];
        snprintf(url_cmd, sizeof(url_cmd), "AT+QHTTPURL=%u,80", (unsigned int)strlen(url));
        if (!send_at_command(url_cmd, "CONNECT", 5000)) {
            return -2;
        }
        serial->print(url);
        delay(500);

        // Send POST body
        char post_cmd[64];
        snprintf(post_cmd, sizeof(post_cmd), "AT+QHTTPPOST=%u,60,60", (unsigned int)data_len);
        if (!send_at_command(post_cmd, "CONNECT", 10000)) {
            return -3;
        }
        serial->write(data, data_len);

        char post_resp[128] = {0};
        if (!send_at_command("", "+QHTTPPOST:", 30000, post_resp, sizeof(post_resp))) {
            return -4;
        }

        // Parse HTTP status code from +QHTTPPOST: 0,200,length
        int err = 0, status_code = 0, content_len = 0;
        char *p = strstr(post_resp, "+QHTTPPOST:");
        if (p && sscanf(p, "+QHTTPPOST: %d,%d,%d", &err, &status_code, &content_len) >= 2) {
            if (err == 0 && response_buf && response_buf_max > 0) {
                send_at_command("AT+QHTTPREAD=30", "+QHTTPREAD: 0", 10000, response_buf, response_buf_max);
            }
            return status_code;
        }

        return -5;
    }
};

