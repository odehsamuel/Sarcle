"""Unit test suite for evidence_registry behavior and verification rules."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from contract_mock import EvidenceRegistryMock, RegistryError
from ed25519_compact import publickey, signature


class TestEvidenceRegistryContract(unittest.TestCase):
    def setUp(self):
        self.registry = EvidenceRegistryMock()
        self.registry.current_timestamp = 1700000000
        self.admin = "G_ADMIN_123"
        self.attester_a = "G_ATTESTER_A"
        self.attester_b = "G_ATTESTER_B"

        self.device_sk = bytes.fromhex(
            "1c8aff950685c2ed4bc3174f3472287b56d9517b9c948127319a09a7a36deac8"
        )
        self.device_pk = publickey(self.device_sk)

        self.analyzer_1 = b"\x01" * 32  # Family 1 (Python)
        self.analyzer_2 = b"\x02" * 32  # Family 2 (Rust)
        self.analyzer_1_alt = b"\x03" * 32  # Family 1 (Alternative Python)

        self.registry.init(self.admin, {"max_divergence_bps": 500, "quorum": 2})
        self.registry.register_device(self.admin, self.device_pk)
        self.registry.add_attester(self.admin, self.attester_a)
        self.registry.add_attester(self.admin, self.attester_b)
        self.registry.allow_analyzer(
            self.admin, self.analyzer_1, metric_id=1, family_id=1
        )
        self.registry.allow_analyzer(
            self.admin, self.analyzer_2, metric_id=1, family_id=2
        )
        self.registry.allow_analyzer(
            self.admin, self.analyzer_1_alt, metric_id=1, family_id=1
        )

    def test_happy_path_and_quorum_agreement(self):
        chal = self.registry.request_challenge(
            self.attester_a, job_ref=1001, device_id=self.device_pk, kind=0
        )
        dummy_img = b"\xaa" * 32
        dummy_roi = b"\xbb" * 32

        msg = self.registry.build_canonical_message(
            self.device_pk,
            job_ref=1001,
            kind=0,
            counter=1,
            timestamp=1700000000,
            challenge=chal,
            image_sha256=dummy_img,
        )
        sig = signature(msg, self.device_sk, self.device_pk)

        obs_id = self.registry.submit_observation(
            attester=self.attester_a,
            job_ref=1001,
            kind=0,
            image_hash=dummy_img,
            roi_hash=dummy_roi,
            metric_id=1,
            challenge=chal,
            counter=1,
            timestamp=1700000000,
            signature=sig,
            analyzer_hash=self.analyzer_1,
            value_bps=5000,
        )
        self.assertEqual(obs_id, 1)

        obs = self.registry.get_observation(obs_id)
        self.assertEqual(obs["status"], "PendingQuorum")
        self.assertIsNone(obs["accepted_value_bps"])

        # Attester B submits Analysis B within tolerance (5400 bps, diff = 400 <= 500)
        self.registry.add_analysis(
            attester=self.attester_b,
            obs_id=obs_id,
            analyzer_hash=self.analyzer_2,
            value_bps=5400,
        )

        obs_final = self.registry.get_observation(obs_id)
        self.assertEqual(obs_final["status"], "Accepted")
        self.assertEqual(obs_final["accepted_value_bps"], 5200)

    def test_boundary_at_tolerance_and_one_over(self):
        # Case 1: Exactly at tolerance (diff = 500)
        chal1 = self.registry.request_challenge(
            self.attester_a, job_ref=1002, device_id=self.device_pk, kind=0
        )
        msg1 = self.registry.build_canonical_message(
            self.device_pk, 1002, 0, 2, 1700000000, chal1, b"\x11" * 32
        )
        sig1 = signature(msg1, self.device_sk, self.device_pk)
        obs1 = self.registry.submit_observation(
            self.attester_a,
            1002,
            0,
            b"\x11" * 32,
            b"\x22" * 32,
            1,
            chal1,
            2,
            1700000000,
            sig1,
            self.analyzer_1,
            5000,
        )
        self.registry.add_analysis(
            self.attester_b, obs1, self.analyzer_2, value_bps=5500
        )
        self.assertEqual(
            self.registry.get_observation(obs1)["status"], "Accepted"
        )
        self.assertEqual(
            self.registry.get_observation(obs1)["accepted_value_bps"], 5250
        )

        # Case 2: One basis point over tolerance (diff = 501)
        chal2 = self.registry.request_challenge(
            self.attester_a, job_ref=1003, device_id=self.device_pk, kind=0
        )
        msg2 = self.registry.build_canonical_message(
            self.device_pk, 1003, 0, 3, 1700000000, chal2, b"\x33" * 32
        )
        sig2 = signature(msg2, self.device_sk, self.device_pk)
        obs2 = self.registry.submit_observation(
            self.attester_a,
            1003,
            0,
            b"\x33" * 32,
            b"\x44" * 32,
            1,
            chal2,
            3,
            1700000000,
            sig2,
            self.analyzer_1,
            5000,
        )
        self.registry.add_analysis(
            self.attester_b, obs2, self.analyzer_2, value_bps=5501
        )
        self.assertEqual(
            self.registry.get_observation(obs2)["status"], "Divergent"
        )
        self.assertIsNone(
            self.registry.get_observation(obs2)["accepted_value_bps"]
        )

    def test_independence_rules_enforcement(self):
        chal = self.registry.request_challenge(
            self.attester_a, job_ref=1004, device_id=self.device_pk, kind=0
        )
        msg = self.registry.build_canonical_message(
            self.device_pk, 1004, 0, 4, 1700000000, chal, b"\x55" * 32
        )
        sig = signature(msg, self.device_sk, self.device_pk)
        obs = self.registry.submit_observation(
            self.attester_a,
            1004,
            0,
            b"\x55" * 32,
            b"\x66" * 32,
            1,
            chal,
            4,
            1700000000,
            sig,
            self.analyzer_1,
            5000,
        )

        # 1. Same attester cannot add second analysis
        with self.assertRaises(RegistryError):
            self.registry.add_analysis(
                self.attester_a, obs, self.analyzer_2, 5100
            )

        # 2. Different attester cannot use same analyzer family (Family 1)
        with self.assertRaises(RegistryError):
            self.registry.add_analysis(
                self.attester_b, obs, self.analyzer_1_alt, 5100
            )

    def test_replayed_challenge_and_monotonic_counter(self):
        chal = self.registry.request_challenge(
            self.attester_a, job_ref=1005, device_id=self.device_pk, kind=0
        )
        msg = self.registry.build_canonical_message(
            self.device_pk, 1005, 0, 10, 1700000000, chal, b"\x77" * 32
        )
        sig = signature(msg, self.device_sk, self.device_pk)

        self.registry.submit_observation(
            self.attester_a,
            1005,
            0,
            b"\x77" * 32,
            b"\x88" * 32,
            1,
            chal,
            10,
            1700000000,
            sig,
            self.analyzer_1,
            4000,
        )

        # Replayed challenge fails
        with self.assertRaises(RegistryError):
            self.registry.submit_observation(
                self.attester_a,
                1005,
                0,
                b"\x77" * 32,
                b"\x88" * 32,
                1,
                chal,
                11,
                1700000000,
                sig,
                self.analyzer_1,
                4000,
            )

        # Non-increasing counter fails with new challenge
        chal2 = self.registry.request_challenge(
            self.attester_a, job_ref=1005, device_id=self.device_pk, kind=1
        )
        msg2 = self.registry.build_canonical_message(
            self.device_pk, 1005, 1, 9, 1700000000, chal2, b"\x77" * 32
        )  # counter 9 <= 10
        sig2 = signature(msg2, self.device_sk, self.device_pk)
        with self.assertRaises(RegistryError):
            self.registry.submit_observation(
                self.attester_a,
                1005,
                1,
                b"\x77" * 32,
                b"\x88" * 32,
                1,
                chal2,
                9,
                1700000000,
                sig2,
                self.analyzer_1,
                4000,
            )


if __name__ == "__main__":
    unittest.main()
