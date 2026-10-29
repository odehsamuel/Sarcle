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


if __name__ == "__main__":
    unittest.main()
