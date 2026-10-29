#pragma once

/**
 * Proof-of-Weeding Edge Capture Firmware
 * Camera Hardware Abstraction Layer (HAL)
 * Supports dynamic sensor detection (OV2640 and OV5640) and size validation (< 64 KB).
 */

#include <Arduino.h>
#include "esp_camera.h"
#include "board_pins.h"

#define MAX_FRAME_SIZE_BYTES (64 * 1024) // 64 KB budget for rural cellular / buffer safety
#define MIN_FRAME_SIZE_BYTES 1024        // Less than 1 KB indicates sensor corruption

enum CameraSensorType {
    SENSOR_UNKNOWN = 0,
    SENSOR_OV2640 = 1,
    SENSOR_OV5640 = 2,
};

struct CameraCaptureResult {
    uint8_t* buffer;
    size_t length;
    camera_fb_t* fb;
    bool success;
    const char* error_msg;
};

class CameraHAL {
private:
    CameraSensorType sensor_type;
    bool initialized;

public:
    CameraHAL() : sensor_type(SENSOR_UNKNOWN), initialized(false) {}

    bool init(framesize_t frame_size = FRAMESIZE_VGA, int jpeg_quality = 12) {
        camera_config_t config;
        config.ledc_channel = LEDC_CHANNEL_0;
        config.ledc_timer = LEDC_TIMER_0;
        config.pin_d0 = Y2_GPIO_NUM;
        config.pin_d1 = Y3_GPIO_NUM;
        config.pin_d2 = Y4_GPIO_NUM;
        config.pin_d3 = Y5_GPIO_NUM;
        config.pin_d4 = Y6_GPIO_NUM;
        config.pin_d5 = Y7_GPIO_NUM;
        config.pin_d6 = Y8_GPIO_NUM;
        config.pin_d7 = Y9_GPIO_NUM;
        config.pin_xclk = XCLK_GPIO_NUM;
        config.pin_pclk = PCLK_GPIO_NUM;
        config.pin_vsync = VSYNC_GPIO_NUM;
        config.pin_href = HREF_GPIO_NUM;
        config.pin_sccb_sda = SIOD_GPIO_NUM;
        config.pin_sccb_scl = SIOC_GPIO_NUM;
        config.pin_pwdn = PWDN_GPIO_NUM;
        config.pin_reset = RESET_GPIO_NUM;
        config.xclk_freq_hz = 20000000;
        config.pixel_format = PIXFORMAT_JPEG;
        config.frame_size = frame_size;
        config.jpeg_quality = jpeg_quality;
        config.fb_count = 1;
        config.grab_mode = CAMERA_GRAB_LATEST;

        // If PSRAM is present, allocate 2 frame buffers for double-buffering
        if (psramFound()) {
            config.fb_count = 2;
        }

        esp_err_t err = esp_camera_init(&config);
        if (err != ESP_OK) {
            Serial.printf("[CAM-HAL] esp_camera_init failed: 0x%x\n", err);
            return false;
        }

        sensor_t* s = esp_camera_sensor_get();
        if (s == nullptr) {
            Serial.println("[CAM-HAL] Failed to query sensor descriptor.");
            sensor_type = SENSOR_UNKNOWN;
        } else {
            if (s->id.PID == OV2640_PID) {
                sensor_type = SENSOR_OV2640;
                Serial.println("[CAM-HAL] Detected sensor: OV2640 (2 Megapixel)");
            } else if (s->id.PID == OV5640_PID) {
                sensor_type = SENSOR_OV5640;
                Serial.println("[CAM-HAL] Detected sensor: OV5640 (5 Megapixel)");
            } else {
                sensor_type = SENSOR_UNKNOWN;
                Serial.printf("[CAM-HAL] Unknown camera sensor PID: 0x%04x\n", s->id.PID);
            }

            // Stabilize exposure and white balance for consistent colorimetry
            s->set_brightness(s, 0);     // -2 to 2
            s->set_contrast(s, 0);       // -2 to 2
            s->set_saturation(s, 0);     // -2 to 2
            s->set_special_effect(s, 0); // No color filter
            s->set_whitebal(s, 1);       // Auto White Balance enabled
            s->set_awb_gain(s, 1);       // Auto White Balance gain enabled
            s->set_wb_mode(s, 0);        // Auto mode
        }

        initialized = true;
        return true;
    }

    CameraCaptureResult capture(size_t max_bytes = MAX_FRAME_SIZE_BYTES) {
        CameraCaptureResult res = { nullptr, 0, nullptr, false, "NOT_INITIALIZED" };
        if (!initialized) return res;

        camera_fb_t* fb = esp_camera_fb_get();
        if (!fb) {
            res.error_msg = "FRAME_BUFFER_NULL";
            return res;
        }

        // Validate frame size constraints
        if (fb->len < MIN_FRAME_SIZE_BYTES) {
            esp_camera_fb_return(fb);
            res.error_msg = "FRAME_TOO_SMALL_CORRUPT";
            return res;
        }

        if (fb->len > max_bytes) {
            esp_camera_fb_return(fb);
            res.error_msg = "FRAME_EXCEEDS_64KB_LIMIT";
            return res;
        }

        // Valid frame
        res.buffer = fb->buf;
        res.length = fb->len;
        res.fb = fb;
        res.success = true;
        res.error_msg = nullptr;
        return res;
    }

    void release(camera_fb_t* fb) {
        if (fb) {
            esp_camera_fb_return(fb);
        }
    }

    const char* get_sensor_name() const {
        switch (sensor_type) {
            case SENSOR_OV2640: return "OmniVision OV2640";
            case SENSOR_OV5640: return "OmniVision OV5640";
            default: return "Generic / Unknown Sensor";
        }
    }

    bool is_initialized() const { return initialized; }
};
