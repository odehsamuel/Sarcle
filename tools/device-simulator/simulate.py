"""Edge Device Simulator for Proof-of-Weeding.

Simulates an ESP32-CAM edge capture device:
- Bootstraps cryptographic Ed25519 keypair
- Requests fresh challenge from Attester A
- Captures procedurally generated synthetic scene
- Builds 115-byte canonical message
- Signs message with Ed25519
- Posts multipart payload to Attester A
"""

import hashlib
import json
import logging
import os
import struct
import sys
import time
from typing import Dict, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "attester-a"))

from ed25519_compact import publickey, signature
from generate import generate_scene

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [DEVICE-SIM] %(message)s"
)
logger = logging.getLogger("device-simulator")

DOMAIN_TAG = b"PoW-OBS-v2"


class EdgeDeviceSimulator:
    def __init__(
        self,
        private_key_hex: Optional[str] = None,
        attester_url: str = "http://127.0.0.1:5000",
    ):
        if private_key_hex:
            self.sk = bytes.fromhex(private_key_hex)
        else:
            # Deterministic device key
            self.sk = bytes.fromhex(
                "1c8aff950685c2ed4bc3174f3472287b56d9517b9c948127319a09a7a36deac8"
            )
        self.pk = publickey(self.sk)
        self.attester_url = attester_url
        self.counter = 0

    def capture_and_sign(
        self,
        job_ref: int,
        kind: int,
        target_cover_bps: int,
        challenge: bytes,
        roi_points: list,
        seed: int = 42,
        noise_level: float = 0.0,
        blur_kernel: int = 0,
        exposure_multiplier: float = 1.0,
        dx: int = 0,
        dy: int = 0,
        timestamp: Optional[int] = None,
    ) -> Tuple[bytes, bytes, bytes, int]:
        """Capture synthetic frame, assemble 115-byte message, and compute Ed25519 signature.

        Returns:
            (raw_message, signature, jpeg_bytes, exact_ground_truth_bps)
        """
        self.counter += 1
        now = int(time.time()) if timestamp is None else timestamp

        # Render synthetic camera scene
        jpeg_bytes, _, gt_bps = generate_scene(
            target_cover_bps=target_cover_bps,
            roi_points=roi_points,
            seed=seed,
            noise_level=noise_level,
            blur_kernel=blur_kernel,
            exposure_multiplier=exposure_multiplier,
            dx=dx,
            dy=dy,
        )

        image_sha256 = hashlib.sha256(jpeg_bytes).digest()

        # Build exact 115-byte message
        msg = bytearray()
        msg.extend(DOMAIN_TAG)
        msg.extend(self.pk)
        msg.extend(struct.pack(">Q", job_ref))
        msg.extend(struct.pack("B", kind))
        msg.extend(struct.pack(">Q", self.counter))
        msg.extend(struct.pack(">Q", now))
        msg.extend(challenge)
        msg.extend(image_sha256)
        assert len(msg) == 115, f"Expected 115 bytes, got {len(msg)}"

        raw_msg = bytes(msg)
        sig = signature(raw_msg, self.sk, self.pk)

        return raw_msg, sig, jpeg_bytes, gt_bps


if __name__ == "__main__":
    sim = EdgeDeviceSimulator()
    logger.info(f"Initialized Simulator device public key: {sim.pk.hex()}")
