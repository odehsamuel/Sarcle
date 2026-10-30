#!/usr/bin/env python3
"""Flash Encryption Tooling & Provisioning Utility.

Supports ESP32 & ESP32-S3 AES-XTS flash encryption workflows using standard
ESP-IDF / espsecure.py conventions.

Safeguards against accidental eFuse burning with an explicit --dry-run flag.
"""

import argparse
import hashlib
import os
import secrets
import sys
from typing import Dict, Tuple


def generate_flash_encryption_key(key_path: str) -> bytes:
    """Generate a 256-bit cryptographically secure AES-XTS key for eFuse burning."""
    key = secrets.token_bytes(32)
    os.makedirs(os.path.dirname(os.path.abspath(key_path)), exist_ok=True)
    with open(key_path, "wb") as f:
        f.write(key)
    return key


def generate_provisioning_manifest(
    key_path: str, mode: str = "development"
) -> Dict[str, str]:
    """Generate eFuse and partition encryption commands based on security mode."""
    if mode not in ["development", "release"]:
        raise ValueError("Mode must be 'development' or 'release'")

    manifest = {
        "mode": mode,
        "key_path": key_path,
        "burn_key_cmd": (
            f"espefuse.py --port /dev/ttyUSB0 burn_key "
            f"{'BLOCK1' if 's3' not in mode else 'BLOCK_KEY0'} {key_path} XTS_AES_256_KEY"
        ),
        "enable_crypt_cmd": (
            "espefuse.py --port /dev/ttyUSB0 burn_efuse FLASH_CRYPT_CNT 1"
            if mode == "development"
            else "espefuse.py --port /dev/ttyUSB0 burn_efuse FLASH_CRYPT_CNT 0x7F FLASH_CRYPT_CONFIG 0xF"
        ),
        "encrypt_bootloader_cmd": (
            f"espsecure.py encrypt_flash_data --keyfile {key_path} --address 0x1000 "
            f"--output .pio/build/esp32cam/bootloader-enc.bin .pio/build/esp32cam/bootloader.bin"
        ),
        "encrypt_partitions_cmd": (
            f"espsecure.py encrypt_flash_data --keyfile {key_path} --address 0x8000 "
            f"--output .pio/build/esp32cam/partitions-enc.bin .pio/build/esp32cam/partitions.bin"
        ),
    }

    if mode == "release":
        manifest["disable_download_mode_cmd"] = (
            "espefuse.py --port /dev/ttyUSB0 burn_efuse DIS_DOWNLOAD_MODE 1"
        )

    return manifest


def main():
    parser = argparse.ArgumentParser(
        description="Proof-of-Weeding Flash Encryption Provisioning Utility"
    )
    parser.add_argument(
        "--output-key",
        type=str,
        default="firmware/esp32cam/keys/flash_encryption_key.bin",
        help="Destination path for generated AES-XTS key",
    )
    parser.add_argument(
        "--mode",
        choices=["development", "release"],
        default="development",
        help="Target security profile ('development' allows re-flashing; 'release' permanently seals eFuses)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print provisioning plan without generating key or burning eFuses",
    )

    args = parser.parse_args()

    print("==================================================")
    print("PROOF-OF-WEEDING FLASH ENCRYPTION PROVISIONING")
    print("==================================================")
    print(f"[*] Target Profile: {args.mode.upper()}")
    print(f"[*] Key Destination: {args.output_key}")

    if args.dry_run:
        print("\n[DRY RUN] Simulating flash encryption configuration:")
        manifest = generate_provisioning_manifest(args.output_key, args.mode)
        for step, cmd in manifest.items():
            print(f"  [{step}] -> {cmd}")
        print("\n[PASS] Dry run completed safely with zero eFuses burned.")
        sys.exit(0)

    # Real key generation
    key = generate_flash_encryption_key(args.output_key)
    key_sha = hashlib.sha256(key).hexdigest()
    print(f"\n[SUCCESS] Generated 256-bit AES-XTS Flash Encryption Key.")
    print(f"[*] Key Fingerprint (SHA-256): {key_sha[:16]}...{key_sha[-8:]}")
    print("\nNext steps to provision target hardware:")
    manifest = generate_provisioning_manifest(args.output_key, args.mode)
    print(f"1. Burn key to eFuse:    {manifest['burn_key_cmd']}")
    print(f"2. Activate encryption:  {manifest['enable_crypt_cmd']}")
    print(f"3. Encrypt bootloader:   {manifest['encrypt_bootloader_cmd']}")


if __name__ == "__main__":
    main()
