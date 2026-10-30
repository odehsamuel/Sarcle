#!/usr/bin/env python3
"""Factory Device Provisioning & On-Chain Registration Utility.

Generates device Ed25519 cryptographic keypairs, prepares NVS factory
partition payloads, and registers the device ID with the evidence_registry contract.
"""

import argparse
import os
import sys
from typing import Dict, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools"))

from chain_client import ChainClient
from ed25519_compact import publickey


def generate_device_keypair() -> Tuple[bytes, bytes]:
    """Generate RFC 8032 compliant Ed25519 private seed and public key."""
    seed = os.urandom(32)
    pub = publickey(seed)
    return seed, pub


def generate_nvs_csv(seed: bytes, pub: bytes, initial_counter: int = 0) -> str:
    """Generate ESP-IDF NVS partition CSV source for secure factory flashing."""
    return f"""key,type,encoding,value
pow_sec,namespace,,
priv_key,data,hex2bin,{seed.hex()}
pub_key,data,hex2bin,{pub.hex()}
cnt_a,data,u64,{initial_counter}
cnt_b,data,u64,{initial_counter}
"""


def provision_and_register_device(
    chain_mode: str = "mock",
    dry_run: bool = False,
    output_nvs_csv: str = None,
) -> Dict[str, str]:
    """Execute complete factory provisioning flow."""
    seed, pub = generate_device_keypair()
    device_id_hex = pub.hex()

    csv_content = generate_nvs_csv(seed, pub, 0)
    if output_nvs_csv and not dry_run:
        os.makedirs(os.path.dirname(os.path.abspath(output_nvs_csv)), exist_ok=True)
        with open(output_nvs_csv, "w", encoding="utf-8") as f:
            f.write(csv_content)

    res = {
        "device_id_hex": device_id_hex,
        "seed_hex": seed.hex(),
        "registered_on_chain": False,
    }

    if not dry_run:
        chain = ChainClient(mode=chain_mode)
        try:
            chain.register_device(chain.admin, device_id_hex)
            res["registered_on_chain"] = True
        except Exception as e:
            res["chain_error"] = str(e)

    return res


def main():
    parser = argparse.ArgumentParser(
        description="Proof-of-Weeding Device Provisioning & Registration Tool"
    )
    parser.add_argument(
        "--chain-mode",
        choices=["mock", "testnet"],
        default="mock",
        help="Target blockchain network for device registration",
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        default="firmware/esp32cam/keys/factory_nvs.csv",
        help="Path to output NVS partition CSV",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate provisioning without modifying files or blockchain state",
    )

    args = parser.parse_args()

    print("==================================================")
    print("PROOF-OF-WEEDING FACTORY DEVICE PROVISIONING")
    print("==================================================")
    print(f"[*] Chain Mode: {args.chain_mode.upper()}")
    print(f"[*] Output CSV: {args.output_csv}")

    res = provision_and_register_device(
        chain_mode=args.chain_mode,
        dry_run=args.dry_run,
        output_nvs_csv=args.output_csv,
    )

    print(f"\n[SUCCESS] Generated Device Public Key: {res['device_id_hex']}")
    if args.dry_run:
        print("[DRY RUN] Skipped on-chain registration and file writes.")
    else:
        print(f"[*] Registered on Evidence Registry: {res['registered_on_chain']}")
        print(f"[*] Factory NVS written to:          {args.output_csv}")


if __name__ == "__main__":
    main()

