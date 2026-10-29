#pragma once

/**
 * Proof-of-Weeding Edge Capture Firmware
 * Cellular Modem Hardware Abstraction Layer (HAL) & AT Command Parser
 *
 * Defines the vendor-neutral modem interface supporting Quectel BG95, SIMCom SIM7080G,
 * and test harness mock implementations for LTE-M and NB-IoT telemetry transport.
 */

#include <Arduino.h>

enum ModemNetworkStatus {
    MODEM_NET_DISCONNECTED = 0,
    MODEM_NET_SEARCHING = 1,
    MODEM_NET_REGISTERED_HOME = 2,
    MODEM_NET_REGISTERED_ROAMING = 3,
    MODEM_NET_DENIED = 4,
    MODEM_NET_ERROR = 5
};

struct SignalMetrics {
    int rssi_dbm;       // -113 dBm to -51 dBm (99 = unknown)
    int ber;            // Bit error rate 0-7 (99 = unknown)
    int rsrp_dbm;       // Reference Signal Received Power
    int rsrq_db;        // Reference Signal Received Quality
    bool signal_ok;
};

enum ATParserState {
    AT_STATE_IDLE = 0,
    AT_STATE_SENDING = 1,
    AT_STATE_WAITING_REPLY = 2,
    AT_STATE_COLLECTING_DATA = 3,
    AT_STATE_SUCCESS = 4,
    AT_STATE_ERROR = 5,
    AT_STATE_TIMEOUT = 6
};

class ICellularModem {
public:
    virtual ~ICellularModem() = default;

    virtual bool power_on() = 0;
    virtual bool power_off() = 0;
    virtual bool reset() = 0;

    virtual bool send_at_command(
        const char *command,
        const char *expected_response,
        uint32_t timeout_ms,
        char *response_buffer = nullptr,
        size_t buffer_size = 0
    ) = 0;

    virtual SignalMetrics get_signal_metrics() = 0;
    virtual ModemNetworkStatus get_network_status() = 0;

    virtual bool configure_apn(const char *apn) = 0;
    virtual bool activate_pdp_context() = 0;
    virtual bool deactivate_pdp_context() = 0;

    virtual int http_post(
        const char *url,
        const uint8_t *data,
        size_t data_len,
        const char *content_type,
        char *response_buf,
        size_t response_buf_max
    ) = 0;
};

class MockCellularModem : public ICellularModem {
private:
    bool powered;
    bool pdp_active;
    String current_apn;
    ModemNetworkStatus mock_status;
    SignalMetrics mock_metrics;

public:
    MockCellularModem()
        : powered(false),
          pdp_active(false),
          mock_status(MODEM_NET_REGISTERED_HOME) {
        mock_metrics.rssi_dbm = -75;
        mock_metrics.ber = 0;
        mock_metrics.rsrp_dbm = -95;
        mock_metrics.rsrq_db = -10;
        mock_metrics.signal_ok = true;
    }

    bool power_on() override {
        powered = true;
        return true;
    }

    bool power_off() override {
        powered = false;
        pdp_active = false;
        return true;
    }

    bool reset() override {
        powered = false;
        pdp_active = false;
        powered = true;
        return true;
    }

    bool send_at_command(
        const char *command,
        const char *expected_response,
        uint32_t timeout_ms,
        char *response_buffer = nullptr,
        size_t buffer_size = 0
    ) override {
        (void)timeout_ms;
        if (!powered) return false;

        if (response_buffer && buffer_size > 0) {
            snprintf(response_buffer, buffer_size, "%s\r\nOK\r\n", expected_response ? expected_response : "OK");
        }
        return true;
    }

    SignalMetrics get_signal_metrics() override {
        return mock_metrics;
    }

    ModemNetworkStatus get_network_status() override {
        return powered ? mock_status : MODEM_NET_DISCONNECTED;
    }

    bool configure_apn(const char *apn) override {
        if (!powered) return false;
        current_apn = apn;
        return true;
    }

    bool activate_pdp_context() override {
        if (!powered) return false;
        pdp_active = true;
        return true;
    }

    bool deactivate_pdp_context() override {
        pdp_active = false;
        return true;
    }

    int http_post(
        const char *url,
        const uint8_t *data,
        size_t data_len,
        const char *content_type,
        char *response_buf,
        size_t response_buf_max
    ) override {
        (void)url;
        (void)data;
        (void)data_len;
        (void)content_type;
        if (!powered || !pdp_active) return -1;
        if (response_buf && response_buf_max > 0) {
            snprintf(response_buf, response_buf_max, "{\"status\":\"ok\"}");
        }
        return 200;
    }
};
