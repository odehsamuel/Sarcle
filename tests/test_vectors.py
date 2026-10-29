"""Test suite verifying canonical test vectors for PoW-OBS-v2."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from ed25519_compact import checkvalid


class TestObservationVectors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        vec_path = os.path.join(
            os.path.dirname(__file__), "..", "docs", "spec", "test-vectors.json"
        )
        with open(vec_path, "r", encoding="utf-8") as f:
            cls.data = json.load(f)

    def test_vector_count(self):
        vectors = self.data.get("vectors", [])
        self.assertGreaterEqual(
            len(vectors), 7, "Must contain at least 7 test vectors"
        )

    def test_vector_spec_compliance(self):
        for vec in self.data["vectors"]:
            vec_id = vec["id"]
            with self.subTest(vector_id=vec_id):
                raw_msg = bytes.fromhex(vec["raw_message_hex"])
                sig = bytes.fromhex(vec["signature_hex"])
                device_pk = bytes.fromhex(vec["device_id_hex"])

                self.assertEqual(
                    len(raw_msg),
                    115,
                    f"Vector {vec_id} message length must be 115 bytes",
                )
                self.assertEqual(
                    len(sig), 64, f"Vector {vec_id} signature length must be 64 bytes"
                )
                self.assertEqual(
                    len(device_pk),
                    32,
                    f"Vector {vec_id} public key length must be 32 bytes",
                )

                # Signature math verification
                sig_valid = checkvalid(sig, raw_msg, device_pk)

                # Vector-specific assertions
                if vec_id == "vec-01-valid-baseline":
                    self.assertTrue(sig_valid)
                    self.assertTrue(vec["expected_valid"])
                    self.assertEqual(vec["kind"], 0)
                elif vec_id == "vec-02-valid-completion":
                    self.assertTrue(sig_valid)
                    self.assertTrue(vec["expected_valid"])
                    self.assertEqual(vec["kind"], 1)
                elif vec_id == "vec-03-invalid-kind":
                    # Cryptographic signature matches the corrupted bytes, but contract logic rejects kind
                    self.assertTrue(sig_valid)
                    self.assertFalse(vec["expected_valid"])
                    self.assertNotIn(vec["kind"], (0, 1, 2))
                elif vec_id in (
                    "vec-04-altered-image-hash",
                    "vec-05-altered-counter",
                    "vec-06-altered-challenge",
                    "vec-07-wrong-key",
                ):
                    self.assertFalse(
                        sig_valid,
                        f"Tampered/mismatched vector {vec_id} must fail cryptographic signature check",
                    )
                    self.assertFalse(vec["expected_valid"])
                elif vec_id == "vec-08-wrong-domain-tag":
                    self.assertFalse(vec["expected_valid"])
                    self.assertNotEqual(vec["domain_tag"], "PoW-OBS-v2")


if __name__ == "__main__":
    unittest.main()
