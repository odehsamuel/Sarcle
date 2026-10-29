#pragma once

/**
 * Proof-of-Weeding Edge Firmware: Board Pinout Abstraction
 * Supports AI-Thinker ESP32-CAM and ESP32-S3 Camera Modules.
 */

#if defined(TARGET_ESP32_S3)

#define BOARD_NAME "ESP32-S3-CAM"

// ESP32-S3 Camera Pin Mapping (Freenove / Xiao ESP32S3 / Standard DVP)
#define PWDN_GPIO_NUM     -1
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM     10
#define SIOD_GPIO_NUM     21
#define SIOC_GPIO_NUM     14

#define Y9_GPIO_NUM       16
#define Y8_GPIO_NUM       18
#define Y7_GPIO_NUM       17
#define Y6_GPIO_NUM       15
#define Y5_GPIO_NUM        6
#define Y4_GPIO_NUM        4
#define Y3_GPIO_NUM        5
#define Y2_GPIO_NUM        7

#define VSYNC_GPIO_NUM    38
#define HREF_GPIO_NUM     47
#define PCLK_GPIO_NUM     13

// LED / Diagnostic Indicators
#define STATUS_LED_PIN    48
#define FLASH_LED_PIN     48
#define LED_ACTIVE_LEVEL  HIGH

#elif defined(TARGET_ESP32_CAM) || !defined(TARGET_ESP32_S3)

#define BOARD_NAME "AI-Thinker ESP32-CAM"

// Classic AI-Thinker ESP32-CAM Pin Mapping
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27

#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5

#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// LED / Diagnostic Indicators
#define STATUS_LED_PIN    33 // Small red LED (Active LOW)
#define FLASH_LED_PIN      4 // High-power spotlight flash LED (Active HIGH)
#define LED_ACTIVE_LEVEL  LOW

#endif
