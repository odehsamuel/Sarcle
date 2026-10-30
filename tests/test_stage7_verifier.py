"""Unit tests for Stage 7: Attester B, Calibration, and Public Re-verifier."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "attester-b"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "tools", "pow-verify")
)
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "tools", "synthetic-scenes")
)

from analyzer_b import analyze_cielab_cover, compute_analyzer_b_hash
from chain_client import ChainClient
from generate import generate_scene
from runner import AttesterBRunner


class TestStage7AttesterBAndVerifier(unittest.TestCase):
    def setUp(self):
        self.roi_points = [
            {"x": 0.1500, "y": 0.2000},
            {"x": 0.8500, "y": 0.2000},
            {"x": 0.8500, "y": 0.8000},
            {"x": 0.1500, "y": 0.8000},
        ]

    def test_analyzer_b_determinism(self):
        jpeg, _, _ = generate_scene(
            target_cover_bps=5000, roi_points=self.roi_points, seed=77
        )
        bps_1, hash_1 = analyze_cielab_cover(jpeg, self.roi_points)
        bps_2, hash_2 = analyze_cielab_cover(jpeg, self.roi_points)

        self.assertEqual(bps_1, bps_2)
        self.assertEqual(hash_1, hash_2)

    def test_attester_b_runner_submits_analysis(self):
        chain = ChainClient(mode="mock")
        runner = AttesterBRunner(chain, attester_addr="G_ATTESTER_B_RUST")

        # Allowlist Analyzer B
        chain.registry_mock.add_attester(chain.admin, "G_ATTESTER_B_RUST")
        chain.registry_mock.allow_analyzer(
            chain.admin, runner.analyzer_hash, metric_id=1, family_id=2
        )

        jpeg, _, _ = generate_scene(
            target_cover_bps=5000, roi_points=self.roi_points, seed=99
        )
        from analyzer import analyze_green_cover
        bps_a, _, _ = analyze_green_cover(jpeg, self.roi_points)

        # Setup observation in PendingQuorum state with matching Analysis A
        chain.registry_mock.observations[999] = {
            "obs_id": 999,
            "job_ref": 100,
            "kind": 0,
            "device_id": b"\x07" * 32,
            "image_hash": b"\x99" * 32,
            "roi_hash": b"\x88" * 32,
            "metric_id": 1,
            "timestamp": 1700000000,
            "analyses": [
                {
                    "attester": "G_ATTESTER_A",
                    "analyzer_hash": b"\x01" * 32,
                    "family_id": 1,
                    "value_bps": bps_a,
                    "recorded_at": 1700000000,
                }
            ],
            "status": "PendingQuorum",
            "accepted_value_bps": None,
        }

        cover_b = runner.process_and_submit(999, jpeg, self.roi_points)

        obs = chain.registry_mock.get_observation(999)
        self.assertEqual(obs["status"], "Accepted")
        self.assertIsNotNone(obs["accepted_value_bps"])

    def test_pow_verify_json_and_auto_roi(self):
        from verify import verify_job_evidence
        # Run verifier in test mode against Job 1 if observations are logged
        obs_log_path = os.path.join(
            os.path.dirname(__file__), "..", "attester-a", "storage", "observations.json"
        )
        if os.path.exists(obs_log_path):
            img_dir = os.path.join(
                os.path.dirname(__file__), "..", "attester-a", "storage", "images"
            )
            success = verify_job_evidence(
                job_id=1,
                image_dir=img_dir,
                roi_file=None,  # test auto-discovery
                as_json=True,
            )
            self.assertTrue(success)


if __name__ == "__main__":
    unittest.main()
