#!/usr/bin/env python3
"""Hardware Debugging (JTAG & UART) Disablement Utility.

Generates and executes eFuse burning sequences to permanently disable JTAG
hardware debugging and lock down UART ROM download mode on production ESP32
and ESP32-S3 field units.
"""

import argparse
import sys
from typing import Dict, List


def generate_jtag_disable_plan(target: str, port: str = "/dev/ttyUSB0") -> Dict[str, List[str]]:
    """Generate commands to disable physical JTAG tapping and UART cache snooping."""
    if target == "esp32":
        return {
            "target": "ESP32 (AI-Thinker CAM)",
            "efuse_commands": [
                f"espefuse.py --port {port} burn_efuse JTAG_DISABLE 1",
                f"espefuse.py --port {port} burn_efuse UART_DOWNLOAD_DIS 1",
            ],
            "verification_commands": [
                f"espefuse.py --port {port} summary",
            ],
        }
    elif target == "esp32s3":
        return {
            "target": "ESP32-S3-CAM",
            "efuse_commands": [
                f"espefuse.py --port {port} burn_efuse DIS_PAD_JTAG 1",
                f"espefuse.py --port {port} burn_efuse DIS_USB_JTAG 1",
                f"espefuse.py --port {port} burn_efuse HARD_DIS_JTAG 1",
                f"espefuse.py --port {port} burn_efuse DIS_DOWNLOAD_ICACHE 1",
                f"espefuse.py --port {port} burn_efuse DIS_DOWNLOAD_DCACHE 1",
            ],
            "verification_commands": [
                f"espefuse.py --port {port} summary",
            ],
        }
    else:
        raise ValueError(f"Unknown target silicon: {target}. Must be 'esp32' or 'esp32s3'.")


def main():
    parser = argparse.ArgumentParser(
        description="Proof-of-Weeding JTAG Hardware Disablement Utility"
    )
    parser.add_argument(
        "--target",
        choices=["esp32", "esp32s3"],
        default="esp32s3",
        help="Target microcontroller architecture",
    )
    parser.add_argument(
        "--port",
        type=str,
        default="/dev/ttyUSB0",
        help="Serial port connected to hardware",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print eFuse burning plan without modifying hardware registers",
    )

    args = parser.parse_args()

    print("==================================================")
    print("PROOF-OF-WEEDING JTAG & BUS HARDENING PROVISIONING")
    print("==================================================")
    print(f"[*] Target: {args.target.upper()}")
    print(f"[*] Port:   {args.port}")

    plan = generate_jtag_disable_plan(args.target, args.port)

    if args.dry_run:
        print("\n[DRY RUN] Generated eFuse Burning Plan:")
        for idx, cmd in enumerate(plan["efuse_commands"], 1):
            print(f"  Step {idx}: {cmd}")
        print("\n[PASS] Dry run completed safely with zero eFuses burned.")
        sys.exit(0)

    print("\n[WARNING] Executing these commands will PERMANENTLY disable JTAG on silicon!")
    print("Run with --dry-run to inspect commands first.")


if __name__ == "__main__":
    main()

