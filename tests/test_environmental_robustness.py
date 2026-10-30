"""Unit tests for Field Optical Robustness & Environmental Quality Gates (Track E)."""

import os
import sys
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


if __name__ == "__main__":
    unittest.main()
