"""Unit tests for Stage 4: Synthetic scenes, Attester A service, and simulator."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "attester-a"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "tools", "synthetic-scenes")
)
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "tools", "device-simulator")
)

from app import app
from analyzer import analyze_green_cover, compute_analyzer_hash
from generate import generate_scene
from quality_gates import QualityGateFailure, run_quality_gates
from simulate import EdgeDeviceSimulator


class TestStage4Simulation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.roi_points = [
            {"x": 0.1500, "y": 0.2000},
            {"x": 0.8500, "y": 0.2000},
            {"x": 0.8500, "y": 0.8000},
            {"x": 0.1500, "y": 0.8000},
        ]
        # Register ROI via API
        res = cls.client.post(
            "/rois",
            json={"name": "test_bed_north", "points": cls.roi_points},
        )
        cls.roi_hash_hex = res.get_json()["roi_hash_hex"]

    def test_analyzer_ground_truth_accuracy(self):
        """Verify ExG analyzer output on procedural synthetic scenes (LABELED SYNTHETIC)."""
        # Test baseline scene targeting 6500 bps
        jpeg_base, _, gt_base_bps = generate_scene(
            target_cover_bps=6500, roi_points=self.roi_points, seed=42
        )
        measured_base, _, _ = analyze_green_cover(jpeg_base, self.roi_points)

        # Difference between synthetic ground truth and classical ExG measurement
        diff_base = abs(measured_base - gt_base_bps)
        self.assertLessEqual(
            diff_base,
            450,
            f"Synthetic baseline ExG error ({diff_base} bps) exceeds calibration tolerance",
        )

        # Test completion scene targeting 800 bps
        jpeg_comp, _, gt_comp_bps = generate_scene(
            target_cover_bps=800, roi_points=self.roi_points, seed=43
        )
        measured_comp, _, _ = analyze_green_cover(jpeg_comp, self.roi_points)
        diff_comp = abs(measured_comp - gt_comp_bps)
        self.assertLessEqual(
            diff_comp,
            300,
            f"Synthetic completion ExG error ({diff_comp} bps) exceeds calibration tolerance",
        )

    def test_quality_gate_underexposed(self):
        """Quality gate rejects extreme underexposure."""
        dark_jpeg, _, _ = generate_scene(
            target_cover_bps=5000,
            roi_points=self.roi_points,
            exposure_multiplier=0.15,
        )
        with self.assertRaises(QualityGateFailure) as ctx:
            run_quality_gates(dark_jpeg, self.roi_points)
        self.assertEqual(ctx.exception.reason, "FRAME_UNDEREXPOSED")

    def test_quality_gate_overexposed(self):
        """Quality gate rejects extreme overexposure."""
        bright_jpeg, _, _ = generate_scene(
            target_cover_bps=5000,
            roi_points=self.roi_points,
            exposure_multiplier=4.5,
        )
        with self.assertRaises(QualityGateFailure) as ctx:
            run_quality_gates(bright_jpeg, self.roi_points)
        self.assertEqual(ctx.exception.reason, "FRAME_OVEREXPOSED")

    def test_quality_gate_blur(self):
        """Quality gate rejects blurry frames (variance of Laplacian <= 50.0)."""
        blurry_jpeg, _, _ = generate_scene(
            target_cover_bps=5000, roi_points=self.roi_points, blur_kernel=21
        )
        with self.assertRaises(QualityGateFailure) as ctx:
            run_quality_gates(blurry_jpeg, self.roi_points)
        self.assertEqual(ctx.exception.reason, "FRAME_TOO_BLURRY")

    def test_quality_gate_camera_moved(self):
        """Quality gate rejects frames when camera displacement is detected."""
        frame_1, _, _ = generate_scene(
            target_cover_bps=5000, roi_points=self.roi_points, seed=10
        )
        # Shifted scene (dx = 60, dy = 45 pixels)
        frame_2_shifted, _, _ = generate_scene(
            target_cover_bps=5000,
            roi_points=self.roi_points,
            seed=10,
            dx=60,
            dy=45,
        )

        with self.assertRaises(QualityGateFailure) as ctx:
            run_quality_gates(
                frame_2_shifted, self.roi_points, prev_jpeg=frame_1
            )
        self.assertIn("CAMERA_MOVED", ctx.exception.reason)

    def test_device_simulator_end_to_end_flow(self):
        """Run complete simulated capture, challenge request, signing, and submission."""
        sim = EdgeDeviceSimulator()

        # 1. Fetch challenge from Attester A
        chal_res = self.client.get(
            f"/challenge?job_ref=5001&kind=0&device_id={sim.pk.hex()}"
        )
        self.assertEqual(chal_res.status_code, 200)
        challenge_hex = chal_res.get_json()["challenge_hex"]
        challenge = bytes.fromhex(challenge_hex)

        # 2. Simulator captures baseline scene and signs 115-byte message
        raw_msg, sig, jpeg_bytes, _ = sim.capture_and_sign(
            job_ref=5001,
            kind=0,
            target_cover_bps=6000,
            challenge=challenge,
            roi_points=self.roi_points,
            seed=123,
        )

        # 3. Post observation to Attester A
        post_res = self.client.post(
            "/observations",
            json={
                "image_hex": jpeg_bytes.hex(),
                "raw_message_hex": raw_msg.hex(),
                "signature_hex": sig.hex(),
                "roi_hash_hex": self.roi_hash_hex,
            },
        )
        self.assertEqual(post_res.status_code, 201)
        data = post_res.get_json()
        self.assertEqual(data["job_ref"], 5001)
        self.assertEqual(data["kind"], 0)
        self.assertGreater(data["cover_bps"], 5000)


if __name__ == "__main__":
    unittest.main()
