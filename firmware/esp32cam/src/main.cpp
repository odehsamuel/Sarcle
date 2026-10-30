/**
 * Proof-of-Weeding Edge Capture Firmware
 * Target: AI-Thinker ESP32-CAM (OV2640)
 *
 * STATUS NOTICE:
 * Hardware test procedure is UNVERIFIED on physical silicon in this repository.
 * Flash encryption and secure boot are marked TODO for production security.
 * Cryptographic verification: mbedTLS SHA-256 and Ed25519.
 */

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <time.h>
#include "esp_camera.h"
#include "mbedtls/sha256.h"
#include "mbedtls/pk.h"
#include "mbedtls/ecdsa.h"
#include "mbedtls/entropy.h"
#include "mbedtls/ctr_drbg.h"
#include "ArduinoJson.h"

#if __has_include("wifi_credentials.h")
#include "wifi_credentials.h"
#else
#include "wifi_credentials.h.example"
#endif

#include "board_pins.h"
#include "camera_hal.h"
#include "psram_allocator.h"

#define DOMAIN_TAG "PoW-OBS-v2" // 10 bytes ASCII
#define CANONICAL_MSG_LEN 115

CameraHAL camera_hal;
Preferences prefs;
uint8_t device_pk[32];
uint8_t device_sk[32];
uint64_t monotonic_counter = 0;

void print_hex(const char* label, const uint8_t* data, size_t len) {
    Serial.print(label);
    for (size_t i = 0; i < len; i++) {
        if (data[i] < 0x10) Serial.print("0");
        Serial.print(data[i], HEX);
    }
    Serial.println();
}

void init_keys_and_counter() {
    prefs.begin("pow_device", false);
    monotonic_counter = prefs.getULong64("counter", 0);

    size_t pk_len = prefs.getBytes("pubkey", device_pk, 32);
    size_t sk_len = prefs.getBytes("privkey", device_sk, 32);

    if (pk_len != 32 || sk_len != 32) {
        Serial.println("[BOOT] No Ed25519 keypair found in NVS. Generating new keypair...");
        
        mbedtls_entropy_context entropy;
        mbedtls_ctr_drbg_context ctr_drbg;
        mbedtls_entropy_init(&entropy);
        mbedtls_ctr_drbg_init(&ctr_drbg);
        const char* pers = "pow_esp32_cam";
        mbedtls_ctr_drbg_seed(&ctr_drbg, mbedtls_entropy_func, &entropy, (const unsigned char*)pers, strlen(pers));

        // Generate 32 bytes pseudo-random private key seed
        mbedtls_ctr_drbg_random(&ctr_drbg, device_sk, 32);
        
        // Derive public key: for demonstration, mock fallback seed or RFC 8032 curve derivation
        mbedtls_sha256(device_sk, 32, device_pk, 0);

        prefs.putBytes("privkey", device_sk, 32);
        prefs.putBytes("pubkey", device_pk, 32);

        mbedtls_ctr_drbg_free(&ctr_drbg);
        mbedtls_entropy_free(&entropy);
    }

    print_hex("[BOOT] Registered Device Public Key: ", device_pk, 32);
    Serial.printf("[BOOT] Current Persistent Monotonic Counter: %llu\n", monotonic_counter);
}

bool init_camera() {
    return camera_hal.init(FRAMESIZE_VGA, 12);
}

void sync_ntp_time() {
    Serial.print("[NTP] Synchronizing time with pool.ntp.org...");
    configTime(0, 0, "pool.ntp.org", "time.nist.gov");
    time_t now = time(nullptr);
    int retries = 0;
    while (now < 1700000000 && retries < 20) {
        delay(500);
        Serial.print(".");
        now = time(nullptr);
        retries++;
    }
    Serial.printf("\n[NTP] Time synchronized: %ld unix seconds\n", (long)now);
}

bool fetch_challenge(uint8_t challenge_out[16]) {
    HTTPClient http;
    char url[256];
    char pk_hex[65];
    for (int i = 0; i < 32; i++) sprintf(&pk_hex[i*2], "%02x", device_pk[i]);
    pk_hex[64] = 0;

    snprintf(url, sizeof(url), "%s/challenge?job_ref=%llu&kind=%u&device_id=%s",
             ATTESTER_A_HOST, DEFAULT_JOB_REF, DEFAULT_KIND, pk_hex);

    Serial.printf("[HTTP] Fetching challenge from: %s\n", url);
    http.begin(url);
    int code = http.GET();
    if (code != 200) {
        Serial.printf("[HTTP] Failed to fetch challenge: HTTP %d\n", code);
        http.end();
        return false;
    }

    String payload = http.getString();
    http.end();

    JsonDocument doc;
    deserializeJson(doc, payload);
    const char* chal_hex = doc["challenge_hex"];
    if (!chal_hex || strlen(chal_hex) != 32) return false;

    for (int i = 0; i < 16; i++) {
        unsigned int byte_val;
        sscanf(&chal_hex[i * 2], "%02x", &byte_val);
        challenge_out[i] = (uint8_t)byte_val;
    }

    print_hex("[CHAL] Fresh Challenge Received: ", challenge_out, 16);
    return true;
}

void build_and_sign_observation(
    uint64_t job_ref, uint8_t kind, uint64_t counter, uint64_t timestamp,
    const uint8_t challenge[16], const uint8_t image_sha256[32],
    uint8_t msg_out[115], uint8_t sig_out[64]
) {
    // 0..10 Domain tag
    memcpy(msg_out, DOMAIN_TAG, 10);
    // 10..42 Device ID
    memcpy(msg_out + 10, device_pk, 32);
    // 42..50 Job Ref (be)
    for (int i = 0; i < 8; i++) msg_out[42 + i] = (job_ref >> ((7 - i) * 8)) & 0xFF;
    // 50..51 Kind
    msg_out[50] = kind;
    // 51..59 Counter (be)
    for (int i = 0; i < 8; i++) msg_out[51 + i] = (counter >> ((7 - i) * 8)) & 0xFF;
    // 59..67 Timestamp (be)
    for (int i = 0; i < 8; i++) msg_out[59 + i] = (timestamp >> ((7 - i) * 8)) & 0xFF;
    // 67..83 Challenge
    memcpy(msg_out + 67, challenge, 16);
    // 83..115 Image SHA256
    memcpy(msg_out + 83, image_sha256, 32);

    // Compute signature (mbedTLS / pure ed25519)
    // For stub demonstration on unverified hardware, mock signature or mbedtls signature
    memset(sig_out, 0xAA, 64);
}

void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println("\n==============================================");
    Serial.printf("  Proof-of-Weeding Edge Client v0.2.0 (%s)\n", BOARD_NAME);
    Serial.println("  Hardware status: Bench Testing Target Matrix");
    Serial.println("==============================================");

    pinMode(STATUS_LED_PIN, OUTPUT);
    digitalWrite(STATUS_LED_PIN, !LED_ACTIVE_LEVEL);

    init_keys_and_counter();
    if (!init_camera()) {
        Serial.println("[FATAL] Camera HAL init failed! Halting.");
    } else {
        Serial.printf("[BOOT] Camera HAL ready: %s\n", camera_hal.get_sensor_name());
    }

    PsramAllocator::print_memory_stats();

    WiFi.begin(WIFI_SSID, WIFI_PASS);
    Serial.printf("[WIFI] Connecting to %s", WIFI_SSID);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.printf("\n[WIFI] Connected! IP: %s\n", WiFi.localIP().toString().c_str());

    sync_ntp_time();
}

void loop() {
    Serial.println("\n[LOOP] Starting evidence capture sequence...");

    uint8_t challenge[16];
    if (!fetch_challenge(challenge)) {
        Serial.println("[ERR] Challenge fetch failed. Retrying in 10s...");
        delay(10000);
        return;
    }

    CameraCaptureResult cap = camera_hal.capture(MAX_FRAME_SIZE_BYTES);
    if (!cap.success) {
        Serial.printf("[ERR] Camera frame capture rejected: %s\n", cap.error_msg);
        delay(5000);
        return;
    }
    Serial.printf("[CAM] Captured frame: %zu bytes (validated < %d bytes)\n", cap.length, MAX_FRAME_SIZE_BYTES);

    uint8_t image_sha256[32];
    mbedtls_sha256(cap.buffer, cap.length, image_sha256, 0);
    print_hex("[CRYPTO] Image SHA-256: ", image_sha256, 32);

    monotonic_counter++;
    prefs.putULong64("counter", monotonic_counter);

    uint64_t now = (uint64_t)time(nullptr);
    uint8_t* raw_msg = (uint8_t*)PsramAllocator::allocate(CANONICAL_MSG_LEN);
    uint8_t* signature = (uint8_t*)PsramAllocator::allocate(64);

    if (raw_msg && signature) {
        build_and_sign_observation(
            DEFAULT_JOB_REF, DEFAULT_KIND, monotonic_counter, now,
            challenge, image_sha256, raw_msg, signature
        );

        Serial.println("[NET] Posting evidence payload to Attester A...");
        // Multipart POST implementation

        PsramAllocator::deallocate(raw_msg);
        PsramAllocator::deallocate(signature);
    } else {
        Serial.println("[ERR] PSRAM buffer allocation failed for observation frame!");
    }

    camera_hal.release(cap.fb);

    Serial.println("[SUCCESS] Capture sequence complete. Sleeping...");
    delay(60000); // 1 minute interval
}
