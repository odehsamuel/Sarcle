#pragma once

/**
 * Proof-of-Weeding Edge Capture Firmware
 * PSRAM Memory Allocator & Zero-Copy Buffer Management
 * Ensures high-bandwidth image and canonical message buffers are allocated in external SPIRAM,
 * preserving internal SRAM for Wi-Fi/Cellular network stacks and crypto engines.
 */

#include <Arduino.h>
#include "esp_heap_caps.h"

class PsramAllocator {
public:
    static void* allocate(size_t size) {
        if (psramFound()) {
            void* ptr = heap_caps_malloc(size, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
            if (ptr != nullptr) {
                return ptr;
            }
            Serial.printf("[PSRAM] SPIRAM alloc failed for %zu bytes! Falling back to internal heap.\n", size);
        }
        return heap_caps_malloc(size, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
    }

    static void* callocate(size_t n, size_t size) {
        size_t total = n * size;
        void* ptr = allocate(total);
        if (ptr != nullptr) {
            memset(ptr, 0, total);
        }
        return ptr;
    }

    static void deallocate(void* ptr) {
        if (ptr != nullptr) {
            free(ptr);
        }
    }

    static void print_memory_stats() {
        size_t free_sram = heap_caps_get_free_size(MALLOC_CAP_INTERNAL);
        size_t min_free_sram = heap_caps_get_minimum_free_size(MALLOC_CAP_INTERNAL);
        size_t free_psram = psramFound() ? heap_caps_get_free_size(MALLOC_CAP_SPIRAM) : 0;
        size_t total_psram = psramFound() ? ESP.getPsramSize() : 0;

        Serial.println("--- [MEM] System Heap Telemetry ---");
        Serial.printf("  Internal SRAM Free:    %zu KB (Min Ever: %zu KB)\n", free_sram / 1024, min_free_sram / 1024);
        if (psramFound()) {
            Serial.printf("  External PSRAM Free:   %zu KB / %zu KB\n", free_psram / 1024, total_psram / 1024);
        } else {
            Serial.println("  External PSRAM:        NOT DETECTED / DISABLED");
        }
        Serial.println("-----------------------------------");
    }
};
