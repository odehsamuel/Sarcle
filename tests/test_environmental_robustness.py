"""Unit tests for Field Optical Robustness & Environmental Quality Gates (Track E)."""

import math
import os
import sys
import time
import unittest
import numpy as np
import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "attester-a"))


class TestEnvironmentalRobustness(unittest.TestCase):
    def setUp(self):
        # Create synthetic test frame (300x300 BGR)
        np.random.seed(42)
        self.test_img = np.zeros((300, 300, 3), dtype=np.uint8)
        # Background soil
        self.test_img[:, :] = (40, 80, 110)
        # Green patch
        self.test_img[100:200, 100:200] = (30, 180, 50)
        # Deep cast shadow on left half
        self.shadow_img = self.test_img.copy()
        self.shadow_img[:, :150] = (self.shadow_img[:, :150] * 0.25).astype(np.uint8)

    def test_illumination_normalizer(self):
        from illumination_normalizer import (
            normalize_illumination,
            detect_and_compensate_shadows,
            estimate_scene_illumination_stats,
        )

        norm_img = normalize_illumination(self.shadow_img)
        self.assertEqual(norm_img.shape, self.shadow_img.shape)

        comp_img, shadow_mask = detect_and_compensate_shadows(self.shadow_img)
        self.assertEqual(comp_img.shape, self.shadow_img.shape)
        self.assertTrue(np.any(shadow_mask > 0))

        # Check that shadow region was brightened
        shadow_mean_before = np.mean(self.shadow_img[:, :150])
        shadow_mean_after = np.mean(comp_img[:, :150])
        self.assertGreater(shadow_mean_after, shadow_mean_before)

        stats = estimate_scene_illumination_stats(self.shadow_img)
        self.assertIn("mean_luminance", stats)
        self.assertIn("shadow_fraction", stats)
        self.assertGreater(stats["shadow_fraction"], 0.2)

    def test_condensation_and_droplet_gate(self):
        from condensation_gate import check_condensation_and_droplets, QualityGateFailure

        # Natural frame with moderate texture: should pass
        natural_frame = self.test_img.copy()
        noise = np.random.normal(0, 6, natural_frame.shape).astype(np.int16)
        natural_frame = np.clip(natural_frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        rep = check_condensation_and_droplets(natural_frame, min_laplacian_var=10.0)
        self.assertFalse(rep["fog_detected"])
        self.assertFalse(rep["droplets_detected"])

        # Heavy fogged image (Gaussian blurred, low contrast): should fail with ERR_CONDENSATION_FOG
        fogged_frame = cv2.GaussianBlur(natural_frame, (51, 51), 15.0)
        with self.assertRaises(QualityGateFailure) as ctx:
            check_condensation_and_droplets(fogged_frame, min_laplacian_var=10.0)
        self.assertEqual(ctx.exception.reason, "ERR_CONDENSATION_FOG")

    def test_solar_glare_and_flare_gate(self):
        from glare_gate import check_solar_glare_and_reflections, QualityGateFailure

        # Normal frame: should pass
        rep = check_solar_glare_and_reflections(self.test_img)
        self.assertFalse(rep["glare_exceeded"])
        self.assertEqual(rep["glare_pixel_count"], 0)

        # Frame with specular glare spot (> 5% of pixels saturated at 255)
        glare_frame = self.test_img.copy()
        glare_frame[50:150, 50:150] = (255, 255, 255)
        with self.assertRaises(QualityGateFailure) as ctx:
            check_solar_glare_and_reflections(glare_frame, max_glare_fraction=0.05)
        self.assertEqual(ctx.exception.reason, "ERR_SOLAR_GLARE")

    def test_lighting_invariant_homography_matcher(self):
        homo_dir = os.path.join(os.path.dirname(__file__), "..", "tools", "homography")
        sys.path.insert(0, homo_dir)
        from frame_alignment import (
            compute_frame_homography,
            warp_roi_polygon,
            FrameAlignmentError,
        )

        # Base textured image
        h, w = 400, 400
        np.random.seed(123)
        base = np.random.randint(40, 220, (h, w, 3), dtype=np.uint8)
        # Add high-contrast feature crosses
        for x, y in [(80, 80), (320, 80), (80, 320), (320, 320), (200, 200), (150, 250), (250, 150)]:
            cv2.circle(base, (x, y), 12, (255, 255, 255), -1)
            cv2.circle(base, (x, y), 6, (0, 0, 0), -1)

        # Create target with small 5px translation and altered lighting
        M = np.float32([[1, 0, 5], [0, 1, 3]])
        shifted = cv2.warpAffine(base, M, (w, h))
        # Shift illumination (darker + different color cast)
        shifted = (shifted * 0.7).astype(np.uint8)

        H, rep = compute_frame_homography(base, shifted)
        self.assertIsNotNone(H)
        self.assertGreater(rep["inliers"], 5)
        self.assertLess(abs(rep["translation_px"] - math.sqrt(5*5 + 3*3)), 2.5)

        # Warp polygon test
        roi = [(0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8)]
        warped_roi = warp_roi_polygon(roi, H)
        self.assertEqual(len(warped_roi), 4)

    def test_challenge_window_adaptor(self):
        from challenge_adaptor import ChallengeWindowAdaptor

        adaptor = ChallengeWindowAdaptor(base_challenge_ttl_sec=300)
        dev_id = "00" * 32

        # Record successive network latency samples
        prof1 = adaptor.record_network_round_trip(dev_id, 4.0, success=True)
        self.assertEqual(prof1["rtt_ema_sec"], 4.0)
        self.assertEqual(prof1["latency_risk"], "LOW")

        # Record high latency spike (e.g. 45-second cellular stall)
        prof2 = adaptor.record_network_round_trip(dev_id, 45.0, success=False)
        self.assertGreater(prof2["rtt_ema_sec"], 4.0)

        # Freshness evaluation
        now = int(time.time())
        is_fresh, diag = adaptor.evaluate_challenge_freshness(dev_id, now - 100, 300, now)
        self.assertTrue(is_fresh)
        self.assertEqual(diag["remaining_sec"], 200)


if __name__ == "__main__":
    unittest.main()
