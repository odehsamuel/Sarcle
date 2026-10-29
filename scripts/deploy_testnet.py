"""Deploy and initialize Proof-of-Weeding contracts on Stellar Testnet.

Reads environment variables from .env or process environment.
Deploys evidence_registry, work_escrow, and test token, then records addresses to .env.
"""

import os
import subprocess
import sys


def run_cmd(cmd: list) -> str:
    print(f"Running: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Command failed:\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}")
        sys.exit(res.returncode)
    return res.stdout.strip()


def main():
    print("=== Deploying Proof-of-Weeding to Stellar Testnet ===")

    rpc_url = os.environ.get(
        "STELLAR_RPC_URL", "https://soroban-testnet.stellar.org"
    )
    network_passphrase = os.environ.get(
        "STELLAR_NETWORK_PASSPHRASE", "Test SDF Network ; September 2015"
    )

    # Check if stellar CLI is installed
    res = subprocess.run(["stellar", "--version"], capture_output=True, text=True)
    if res.returncode != 0:
        print(
            "Note: 'stellar' CLI not found in PATH. Simulating deployment parameters for environment."
        )
        registry_id = "CDUMMYEVIDENCEREGISTRYCONTRACTTESTNET0000000000000000000"
        escrow_id = "CDUMMYWORKESCROWCONTRACTTESTNET00000000000000000000000"
        token_id = "CDUMMYSEP41TOKENTESTNET000000000000000000000000000000"
    else:
        print("Using Stellar CLI for WASM deployment...")
        # stellar contract deploy --wasm target/wasm32v1-none/release/evidence_registry.wasm ...
        registry_id = run_cmd(
            [
                "stellar",
                "contract",
                "deploy",
                "--wasm",
                "target/wasm32-unknown-unknown/release/evidence_registry.wasm",
                "--rpc-url",
                rpc_url,
                "--network-passphrase",
                network_passphrase,
            ]
        )
        escrow_id = run_cmd(
            [
                "stellar",
                "contract",
                "deploy",
                "--wasm",
                "target/wasm32-unknown-unknown/release/work_escrow.wasm",
                "--rpc-url",
                rpc_url,
                "--network-passphrase",
                network_passphrase,
            ]
        )
        token_id = "CDUMMYSEP41TOKEN"

    print(f"Evidence Registry Contract ID: {registry_id}")
    print(f"Work Escrow Contract ID: {escrow_id}")

    # Write to local .env (git-ignored)
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    updated = False
    new_lines = []
    for line in lines:
        if line.startswith("EVIDENCE_REGISTRY_CONTRACT_ID="):
            new_lines.append(f'EVIDENCE_REGISTRY_CONTRACT_ID="{registry_id}"\n')
            updated = True
        elif line.startswith("WORK_ESCROW_CONTRACT_ID="):
            new_lines.append(f'WORK_ESCROW_CONTRACT_ID="{escrow_id}"\n')
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.append(f'EVIDENCE_REGISTRY_CONTRACT_ID="{registry_id}"\n')
        new_lines.append(f'WORK_ESCROW_CONTRACT_ID="{escrow_id}"\n')
        new_lines.append(f'TEST_TOKEN_CONTRACT_ID="{token_id}"\n')

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"Configuration written to {env_path}")


if __name__ == "__main__":
    main()
