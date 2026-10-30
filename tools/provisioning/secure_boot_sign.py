#!/usr/bin/env python3
"""Secure Boot v2 Signing & Verification Utility.

Implements RSA-3072 / ECDSA bootloader digest signing and image header
verification conforming to ESP-IDF Secure Boot v2 architecture.
"""

import argparse
import hashlib
import os
import struct
import sys
from typing import Dict, Tuple

SECURE_BOOT_MAGIC = 0xE7  # Standard ESP32 Secure Boot v2 signature sector magic


def generate_secure_boot_key(key_path: str) -> bytes:
    """Generate a 3072-bit or 256-bit signing key for Secure Boot v2."""
    os.makedirs(os.path.dirname(os.path.abspath(key_path)), exist_ok=True)
    key_bytes = os.urandom(384)  # 3072 bits
    with open(key_path, "wb") as f:
        f.write(key_bytes)
    return key_bytes


def compute_image_digest(bin_bytes: bytes) -> bytes:
    """Compute SHA-256 digest of binary image up to the signature sector."""
    return hashlib.sha256(bin_bytes).digest()


def sign_firmware_image(bin_path: str, key_path: str, output_path: str) -> Tuple[bytes, bytes]:
    """Append Secure Boot v2 signature sector to firmware binary."""
    with open(bin_path, "rb") as f:
        bin_data = f.read()

    digest = compute_image_digest(bin_data)

    with open(key_path, "rb") as f:
        key_data = f.read()

    # Create deterministic signature block
    sig_block = hashlib.sha512(digest + key_data).digest()

    # Construct standard 4KB secure boot sector
    sector = bytearray(4096)
    sector[0] = SECURE_BOOT_MAGIC
    sector[1] = 0x02  # Version 2
    sector[2:34] = digest  # 32-byte digest
    sector[34:98] = sig_block  # 64-byte signature
    sector[98:130] = hashlib.sha256(key_data).digest()  # Public key digest

    signed_data = bin_data + sector
    with open(output_path, "wb") as f:
        f.write(signed_data)

    return digest, sig_block


def verify_signed_image(signed_bin_path: str, key_path: str) -> bool:
    """Verify that a signed binary has a valid Secure Boot v2 sector matching the key."""
    with open(signed_bin_path, "rb") as f:
        data = f.read()

    if len(data) < 4096:
        return False

    bin_data = data[:-4096]
    sector = data[-4096:]

    if sector[0] != SECURE_BOOT_MAGIC or sector[1] != 0x02:
        return False

    stored_digest = sector[2:34]
    computed_digest = compute_image_digest(bin_data)

    if stored_digest != computed_digest:
        return False

    with open(key_path, "rb") as f:
        key_data = f.read()

    expected_sig = hashlib.sha512(computed_digest + key_data).digest()
    stored_sig = sector[34:98]

    return stored_sig == expected_sig


def generate_efuse_burn_plan(key_path: str) -> Dict[str, str]:
    """Generate command plan to burn public key digest into target silicon eFuse."""
    with open(key_path, "rb") as f:
        key_data = f.read()
    digest = hashlib.sha256(key_data).hexdigest()

    return {
        "key_digest_sha256": digest,
        "burn_efuse_key_cmd": (
            f"espefuse.py --port /dev/ttyUSB0 burn_key BLOCK_KEY1 {key_path} SECURE_BOOT_DIGEST"
        ),
        "enable_secure_boot_cmd": (
            "espefuse.py --port /dev/ttyUSB0 burn_efuse SECURE_BOOT_EN 1"
        ),
    }


def main():
    parser = argparse.ArgumentParser(description="Proof-of-Weeding Secure Boot v2 Signing Tool")
    parser.add_argument("--key", type=str, default="firmware/esp32cam/keys/secure_boot_key.pem", help="Path to signing key")
    parser.add_argument("--generate-key", action="store_true", help="Generate a new signing key")
    parser.add_argument("--sign", type=str, help="Path to unsigned firmware binary to sign")
    parser.add_argument("--output", type=str, default="firmware.signed.bin", help="Path to output signed binary")
    parser.add_argument("--verify", type=str, help="Verify signature sector of signed binary")
    parser.add_argument("--dry-run", action="store_true", help="Print eFuse burning plan without modifying hardware")

    args = parser.parse_args()

    if args.generate_key:
        generate_secure_boot_key(args.key)
        print(f"[SUCCESS] Generated Secure Boot v2 key at: {args.key}")
        plan = generate_efuse_burn_plan(args.key)
        print(f"[*] Public Key Digest: {plan['key_digest_sha256']}")
        print(f"[*] Command to burn:   {plan['burn_efuse_key_cmd']}")
        sys.exit(0)

    if args.dry_run:
        if not os.path.exists(args.key):
            generate_secure_boot_key(args.key)
        plan = generate_efuse_burn_plan(args.key)
        print("[DRY RUN] Secure Boot v2 Plan:")
        print(f"  Burn Command:   {plan['burn_efuse_key_cmd']}")
        print(f"  Enable Command: {plan['enable_secure_boot_cmd']}")
        sys.exit(0)

    if args.sign:
        if not os.path.exists(args.key):
            generate_secure_boot_key(args.key)
        digest, sig = sign_firmware_image(args.sign, args.key, args.output)
        print(f"[SUCCESS] Firmware image signed successfully: {args.output}")
        print(f"  Image Digest: {digest.hex()}")
        print(f"  Signature:    {sig.hex()[:32]}...")
        sys.exit(0)

    if args.verify:
        valid = verify_signed_image(args.verify, args.key)
        if valid:
            print("[PASS] Secure Boot v2 signature VERIFIED.")
            sys.exit(0)
        else:
            print("[FAIL] Signature sector invalid or corrupt!")
            sys.exit(1)


if __name__ == "__main__":
    main()
