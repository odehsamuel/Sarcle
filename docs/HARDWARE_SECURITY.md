# Hardware Security Architecture & eFuse Lifecycle

> **Classification:** Silicon Security Specification  
> **Target Silicon:** Espressif ESP32-D0WD (AI-Thinker) & ESP32-S3-WROOM-1 (N16R8)  
> **Firmware Version:** v0.2.0 (Phase 2 Silicon Hardening)  
> **Threat Mitigation:** Threat Vector 7 ([`docs/THREAT_MODEL.md`](THREAT_MODEL.md) — Edge Camera Key Theft & Physical Extraction)

---

## 1. Threat Context & Security Objectives

In agricultural settings, edge cameras operate on remote, unattended field plots. An adversary with physical access to the device can attempt to:
1. Connect to UART0/UART1 header pins and dump the SPI flash contents.
2. Desolder the SPI NOR flash chip and read plaintext private keys using an external EEPROM programmer.
3. Tamper with the monotonic counter stored in flash memory to execute observation replay attacks.

### Security Objectives
- **Data at Rest Confidentiality:** All flash sectors (firmware binary, NVS partition, device Ed25519 seed) must be encrypted with AES-XTS.
- **Boot Integrity:** The bootloader must verify the cryptographic signature of the application binary before execution.
- **Bus Protection:** Hardware debugging interfaces (JTAG, UART ROM download mode) must be permanently disabled on production units via hardware eFuse burning.

---

## 2. Flash Encryption Architecture (AES-XTS)

Espressif silicon features a dedicated hardware cryptographic accelerator that performs inline AES-XTS transparent decryption between the SPI flash controller and the CPU cache.

```
┌─────────────────────────────────┐
│     SPI NOR FLASH (Encrypted)   │
│  [Bootloader] [NVS] [App Image] │
└────────────────┬────────────────┘
                 │ (Raw Encrypted Ciphertext)
                 ▼
┌─────────────────────────────────┐
│   Hardware AES-XTS Accelerator  │ ◀── [Physical eFuse Key] (Write/Read Protected)
└────────────────┬────────────────┘
                 │ (Decrypted Plaintext in Cache)
                 ▼
┌─────────────────────────────────┐
│         Xtensa Core CPU         │
└─────────────────────────────────┘
```

### Encryption Key Management
- A 256-bit random key is burned into eFuse block `BLOCK1` (ESP32) or `BLOCK_KEY0` (ESP32-S3).
- eFuse read and write disable bits are blown, ensuring that **neither CPU software nor external JTAG probes can read back the physical key**.

---

## 3. Developer Mode vs Production Release Mode

| Parameter | Development Profile | Production Release Profile |
| :--- | :--- | :--- |
| **`FLASH_CRYPT_CNT`** | 1 (Allows re-flashing up to 3 times) | `0x7F` (Permanently locked) |
| **`FLASH_CRYPT_CONFIG`** | `0xF` (All blocks encrypted) | `0xF` (All blocks encrypted) |
| **`DIS_DOWNLOAD_MODE`** | 0 (UART bootloader active) | 1 (UART bootloader disabled) |
| **`JTAG_DISABLE`** | 0 (Debug headers functional) | 1 (JTAG pins permanently burned) |
| **Re-flashing Capability**| Supported via USB-UART | **Disabled (OTA update only)** |

---

## 4. Provisioning Workflow

To provision a physical field device:

```bash
# 1. Run dry-run inspection to verify generated eFuse commands
python tools/provisioning/enable_flash_encryption.py --dry-run --mode development

# 2. Generate cryptographically secure AES-XTS key
python tools/provisioning/enable_flash_encryption.py \
  --output-key firmware/esp32cam/keys/flash_encryption_key.bin \
  --mode development

# 3. Burn key to target microcontroller via espefuse (requires physical USB connection)
espefuse.py --port /dev/ttyUSB0 burn_key BLOCK1 \
  firmware/esp32cam/keys/flash_encryption_key.bin XTS_AES_256_KEY
```
