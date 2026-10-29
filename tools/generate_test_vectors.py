"""Generate canonical test vectors for PoW-OBS-v2 format.

Outputs to docs/spec/test-vectors.json.
"""

import json
import struct
import hashlib
import os
import sys

# Add tools directory to path
sys.path.insert(0, os.path.dirname(__file__))
from ed25519_compact import publickey, signature, checkvalid

# Deterministic private keys for test devices
DEVICE_A_SK = bytes.fromhex(
    "1c8aff950685c2ed4bc3174f3472287b56d9517b9c948127319a09a7a36deac8"
)
DEVICE_A_PK = publickey(DEVICE_A_SK)

DEVICE_B_SK = bytes.fromhex(
    "2b6f1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab"
)
DEVICE_B_PK = publickey(DEVICE_B_SK)

DOMAIN_TAG = b"PoW-OBS-v2"  # 10 bytes


def build_message(
    domain_tag: bytes,
    device_pk: bytes,
    job_ref: int,
    kind: int,
    counter: int,
    timestamp: int,
    challenge: bytes,
    image_sha256: bytes,
) -> bytes:
    msg = bytearray()
    msg.extend(domain_tag)
    msg.extend(device_pk)
    msg.extend(struct.pack(">Q", job_ref))
    msg.extend(struct.pack("B", kind))
    msg.extend(struct.pack(">Q", counter))
    msg.extend(struct.pack(">Q", timestamp))
    msg.extend(challenge)
    msg.extend(image_sha256)
    assert len(msg) == 115, f"Expected 115 bytes, got {len(msg)}"
    return bytes(msg)


def main():
    dummy_img_a = hashlib.sha256(b"procedural_synthetic_frame_0").digest()
    dummy_img_b = hashlib.sha256(b"procedural_synthetic_frame_1").digest()
    dummy_img_c = hashlib.sha256(b"procedural_synthetic_frame_2").digest()

    challenge_0 = bytes.fromhex("11223344556677889900aabbccddeeff")
    challenge_1 = bytes.fromhex("ffeeddccbbaa00998877665544332211")

    vectors = []

    # Vector 1: Valid Baseline
    msg1 = build_message(
        DOMAIN_TAG,
        DEVICE_A_PK,
        job_ref=1001,
        kind=0,
        counter=1,
        timestamp=1700000000,
        challenge=challenge_0,
        image_sha256=dummy_img_a,
    )
    sig1 = signature(msg1, DEVICE_A_SK, DEVICE_A_PK)
    assert checkvalid(sig1, msg1, DEVICE_A_PK)
    vectors.append(
        {
            "id": "vec-01-valid-baseline",
            "description": "Valid baseline observation frame signed by Device A",
            "domain_tag": DOMAIN_TAG.decode("ascii"),
            "device_id_hex": DEVICE_A_PK.hex(),
            "device_priv_hex": DEVICE_A_SK.hex(),
            "job_ref": 1001,
            "kind": 0,
            "counter": 1,
            "timestamp": 1700000000,
            "challenge_hex": challenge_0.hex(),
            "image_sha256_hex": dummy_img_a.hex(),
            "raw_message_hex": msg1.hex(),
            "signature_hex": sig1.hex(),
            "expected_valid": True,
            "expected_failure_reason": None,
        }
    )

    # Vector 2: Valid Completion (counter strictly increased, new challenge)
    msg2 = build_message(
        DOMAIN_TAG,
        DEVICE_A_PK,
        job_ref=1001,
        kind=1,
        counter=2,
        timestamp=1700003600,
        challenge=challenge_1,
        image_sha256=dummy_img_b,
    )
    sig2 = signature(msg2, DEVICE_A_SK, DEVICE_A_PK)
    assert checkvalid(sig2, msg2, DEVICE_A_PK)
    vectors.append(
        {
            "id": "vec-02-valid-completion",
            "description": "Valid completion observation frame with incremented counter and fresh challenge",
            "domain_tag": DOMAIN_TAG.decode("ascii"),
            "device_id_hex": DEVICE_A_PK.hex(),
            "device_priv_hex": DEVICE_A_SK.hex(),
            "job_ref": 1001,
            "kind": 1,
            "counter": 2,
            "timestamp": 1700003600,
            "challenge_hex": challenge_1.hex(),
            "image_sha256_hex": dummy_img_b.hex(),
            "raw_message_hex": msg2.hex(),
            "signature_hex": sig2.hex(),
            "expected_valid": True,
            "expected_failure_reason": None,
        }
    )

    # Vector 3: Invalid Kind (kind = 9 is out of range 0..2)
    msg3 = build_message(
        DOMAIN_TAG,
        DEVICE_A_PK,
        job_ref=1001,
        kind=9,
        counter=3,
        timestamp=1700007200,
        challenge=challenge_1,
        image_sha256=dummy_img_c,
    )
    sig3 = signature(msg3, DEVICE_A_SK, DEVICE_A_PK)
    vectors.append(
        {
            "id": "vec-03-invalid-kind",
            "description": "Signature is mathematically valid over message, but kind (9) is invalid (must be 0, 1, or 2)",
            "domain_tag": DOMAIN_TAG.decode("ascii"),
            "device_id_hex": DEVICE_A_PK.hex(),
            "device_priv_hex": DEVICE_A_SK.hex(),
            "job_ref": 1001,
            "kind": 9,
            "counter": 3,
            "timestamp": 1700007200,
            "challenge_hex": challenge_1.hex(),
            "image_sha256_hex": dummy_img_c.hex(),
            "raw_message_hex": msg3.hex(),
            "signature_hex": sig3.hex(),
            "expected_valid": False,
            "expected_failure_reason": "INVALID_OBSERVATION_KIND",
        }
    )

    # Vector 4: Altered Image Hash (tampered image_sha256 bytes)
    tampered_img = hashlib.sha256(b"tampered_fake_image").digest()
    msg4_tampered = build_message(
        DOMAIN_TAG,
        DEVICE_A_PK,
        job_ref=1001,
        kind=0,
        counter=1,
        timestamp=1700000000,
        challenge=challenge_0,
        image_sha256=tampered_img,
    )
    vectors.append(
        {
            "id": "vec-04-altered-image-hash",
            "description": "Image SHA-256 in message was altered after signature generation",
            "domain_tag": DOMAIN_TAG.decode("ascii"),
            "device_id_hex": DEVICE_A_PK.hex(),
            "device_priv_hex": DEVICE_A_SK.hex(),
            "job_ref": 1001,
            "kind": 0,
            "counter": 1,
            "timestamp": 1700000000,
            "challenge_hex": challenge_0.hex(),
            "image_sha256_hex": tampered_img.hex(),
            "raw_message_hex": msg4_tampered.hex(),
            "signature_hex": sig1.hex(),  # sig1 was for dummy_img_a
            "expected_valid": False,
            "expected_failure_reason": "SIGNATURE_VERIFICATION_FAILED",
        }
    )

    # Vector 5: Altered Counter (counter rolled back / replayed)
    msg5_tampered = build_message(
        DOMAIN_TAG,
        DEVICE_A_PK,
        job_ref=1001,
        kind=1,
        counter=1,
        timestamp=1700003600,
        challenge=challenge_1,
        image_sha256=dummy_img_b,
    )  # counter=1 instead of 2
    vectors.append(
        {
            "id": "vec-05-altered-counter",
            "description": "Counter in message payload was altered/replayed, violating signature",
            "domain_tag": DOMAIN_TAG.decode("ascii"),
            "device_id_hex": DEVICE_A_PK.hex(),
            "device_priv_hex": DEVICE_A_SK.hex(),
            "job_ref": 1001,
            "kind": 1,
            "counter": 1,
            "timestamp": 1700003600,
            "challenge_hex": challenge_1.hex(),
            "image_sha256_hex": dummy_img_b.hex(),
            "raw_message_hex": msg5_tampered.hex(),
            "signature_hex": sig2.hex(),  # sig2 was for counter=2
            "expected_valid": False,
            "expected_failure_reason": "SIGNATURE_VERIFICATION_FAILED",
        }
    )

    # Vector 6: Altered Challenge (nonce does not match signature)
    tampered_challenge = bytes.fromhex("00000000000000000000000000000000")
    msg6_tampered = build_message(
        DOMAIN_TAG,
        DEVICE_A_PK,
        job_ref=1001,
        kind=0,
        counter=1,
        timestamp=1700000000,
        challenge=tampered_challenge,
        image_sha256=dummy_img_a,
    )
    vectors.append(
        {
            "id": "vec-06-altered-challenge",
            "description": "Challenge nonce modified from issued value, causing signature verification failure",
            "domain_tag": DOMAIN_TAG.decode("ascii"),
            "device_id_hex": DEVICE_A_PK.hex(),
            "device_priv_hex": DEVICE_A_SK.hex(),
            "job_ref": 1001,
            "kind": 0,
            "counter": 1,
            "timestamp": 1700000000,
            "challenge_hex": tampered_challenge.hex(),
            "image_sha256_hex": dummy_img_a.hex(),
            "raw_message_hex": msg6_tampered.hex(),
            "signature_hex": sig1.hex(),
            "expected_valid": False,
            "expected_failure_reason": "SIGNATURE_VERIFICATION_FAILED",
        }
    )

    # Vector 7: Wrong Key (verified against unregistered / different Device B public key)
    vectors.append(
        {
            "id": "vec-07-wrong-key",
            "description": "Message was signed by Device A, but verified against Device B public key",
            "domain_tag": DOMAIN_TAG.decode("ascii"),
            "device_id_hex": DEVICE_B_PK.hex(),  # Wrong device key
            "device_priv_hex": DEVICE_A_SK.hex(),
            "job_ref": 1001,
            "kind": 0,
            "counter": 1,
            "timestamp": 1700000000,
            "challenge_hex": challenge_0.hex(),
            "image_sha256_hex": dummy_img_a.hex(),
            "raw_message_hex": msg1.hex(),
            "signature_hex": sig1.hex(),
            "expected_valid": False,
            "expected_failure_reason": "SIGNATURE_VERIFICATION_FAILED",
        }
    )

    # Vector 8: Wrong Domain Tag ("PoW-OBS-v1" instead of "PoW-OBS-v2")
    wrong_domain = b"PoW-OBS-v1"
    msg8 = build_message(
        wrong_domain,
        DEVICE_A_PK,
        job_ref=1001,
        kind=0,
        counter=1,
        timestamp=1700000000,
        challenge=challenge_0,
        image_sha256=dummy_img_a,
    )
    sig8 = signature(msg8, DEVICE_A_SK, DEVICE_A_PK)
    vectors.append(
        {
            "id": "vec-08-wrong-domain-tag",
            "description": "Message utilizes outdated or spoofed domain tag (PoW-OBS-v1)",
            "domain_tag": wrong_domain.decode("ascii"),
            "device_id_hex": DEVICE_A_PK.hex(),
            "device_priv_hex": DEVICE_A_SK.hex(),
            "job_ref": 1001,
            "kind": 0,
            "counter": 1,
            "timestamp": 1700000000,
            "challenge_hex": challenge_0.hex(),
            "image_sha256_hex": dummy_img_a.hex(),
            "raw_message_hex": msg8.hex(),
            "signature_hex": sig8.hex(),
            "expected_valid": False,
            "expected_failure_reason": "INVALID_DOMAIN_TAG",
        }
    )

    out_path = os.path.join(
        os.path.dirname(__file__), "..", "docs", "spec", "test-vectors.json"
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "schema_version": "2.0",
                "format": "PoW-OBS-v2",
                "total_message_bytes": 115,
                "vectors": vectors,
            },
            f,
            indent=2,
        )
    print(f"Generated {len(vectors)} test vectors to {out_path}")


if __name__ == "__main__":
    main()
