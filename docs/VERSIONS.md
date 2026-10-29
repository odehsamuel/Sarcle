# Tooling and Dependency Versions

This document records the exact versions, targets, and justifications pinned for Proof-of-Weeding across smart contracts, services, edge firmware, and web dashboard.

---

## 1. Stellar Smart Contracts (Soroban)

| Component | Selected Version / Target | Justification & Official Alignment |
| :--- | :--- | :--- |
| **`soroban-sdk`** | `22.0.8` (Protocol 22) | Current stable SDK on crates.io supporting Protocol 22 features, `soroban_sdk::crypto::Crypto::ed25519_verify`, PRNG APIs, SEP-41 client definitions, and test environment host. |
| **Rust Compiler** | `1.84+` (stable) | Required compiler version for Soroban SDK v22 and modern Rust 2024 edition features. |
| **WASM Build Target** | `wasm32v1-none` (preferred) / `wasm32-unknown-unknown` | Soroban contracts target WebAssembly. Protocol 21+ and `stellar-cli` v22 prefer `wasm32v1-none` (standardizing WASM v1 feature set without OS imports). `wasm32-unknown-unknown` is retained as fallback. |
| **Stellar CLI** | `stellar-cli 22.x` | Official toolchain binary replacing `soroban-cli`. Handles `stellar contract build`, `stellar contract deploy`, `stellar contract invoke`, and constructor argument passing (CAP-58). |

---

## 2. Attestation Services & Analyzers

| Component | Selected Version | Justification & Official Alignment |
| :--- | :--- | :--- |
| **Python** | `3.14.x` / `>= 3.11` | Runtime environment for Attester A and synthetic scene generator. |
| **OpenCV (Python)** | `opencv-python-headless 4.10.x` | Classical CV analyzer for Excess Green (ExG) index, Otsu thresholding, Laplacian blur estimation, and ORB feature homography. Headless distribution prevents GUI dependencies in headless server environments. |
| **NumPy** | `numpy >= 2.0.0` | Matrix manipulations and chromaticity normalizations. |
| **Flask** | `flask >= 3.0.0` | Lightweight HTTP API framework for Attester A challenge and evidence ingestion endpoints. |
| **`stellar-sdk` (Python)**| `stellar-sdk >= 9.3.0` | Official Python client library for Horizon and Soroban RPC. Supports Ed25519 keypairs and XDR envelope construction. |
| **Image Crate (Rust)** | `image 0.25.x` | Pure-Rust dependency used by Attester B for zero-external-dependency JPEG decoding and fixed-point CIELAB $a^*$ channel segmentation. |

---

## 3. Web Dashboard

| Component | Selected Version | Justification & Official Alignment |
| :--- | :--- | :--- |
| **Node.js** | `v24.x` / `>= 20.x` LTS | Modern JS runtime with native fetch and WebCrypto. |
| **React** | `18.3.x` | Framework for reactive UI state machine visualization. |
| **Vite** | `6.x` / `5.x` | Fast modern bundler with TypeScript support. |
| **`@stellar/stellar-sdk`** | `^13.0.0` | Official JavaScript/TypeScript SDK for Stellar RPC interaction, contract invocation parsing, and account balance monitoring. |
| **`@creit-tech/stellar-wallets-kit`** | `^1.x` | Official modular wallet kit providing plug-and-play Freighter and Albedo wallet connectors for Stellar Testnet. |

---

## 4. Edge Firmware (ESP32-CAM)

| Component | Selected Version | Justification & Official Alignment |
| :--- | :--- | :--- |
| **Target Platform** | PlatformIO `espressif32 @ ~6.8.0` | Stable ESP32 Arduino framework build. |
| **Hardware** | AI-Thinker ESP32-CAM (ESP32-D0WD, OV2640 sensor) | Low-cost, ubiquitously accessible edge camera with 4MB PSRAM. |
| **Cryptography** | `mbedTLS 2.28.x` / `libsodium` | Native ESP-IDF mbedTLS provides hardware-accelerated SHA-256 and Ed25519 signature computation with zero third-party dynamic libraries. |
| **NVS Driver** | `Preferences.h` / `nvs_flash.h` | Persistent non-volatile storage for private key and monotonic replay counter across power cycles. |

---

## 5. Verification Policy

Prior to committing dependencies or generating build lockfiles:
1. Every version is validated against upstream registries (Crates.io, PyPI, npmjs).
2. Contracts must compile without warnings under `cargo clippy -- -D warnings`.
3. Off-chain analyzers pin deterministic algorithm hashes: `analyzer_hash = SHA256(canonical_json({algorithm_id, algorithm_version, parameters}))`.
