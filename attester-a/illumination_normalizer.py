"""Diurnal Solar Illumination Normalization & Shadow Compensation Filter.

Mitigates diurnal lighting fluctuations, harsh cast shadows, and color temperature
shifts across multi-week agricultural observation epochs without altering
chromatic vegetation indices (ExG).
"""

from typing import Dict, Tuple
import cv2
import numpy as np


def normalize_illumination(
    img_bgr: np.ndarray,
    clip_limit: float = 2.0,
    tile_grid_size: Tuple[int, int] = (8, 8),
) -> np.ndarray:
    """Normalize illumination using CLAHE on the CIE-LAB Luminance (L*) channel.

    Strictly preserves A* and B* chromatic channels to avoid corrupting ExG ratios.
    """
    if img_bgr is None or img_bgr.size == 0:
        raise ValueError("Invalid input image")

    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    l_norm = clahe.apply(l_channel)

    lab_norm = cv2.merge((l_norm, a_channel, b_channel))
    return cv2.cvtColor(lab_norm, cv2.COLOR_LAB2BGR)


def detect_and_compensate_shadows(
    img_bgr: np.ndarray,
    shadow_luminance_threshold: float = 50.0,
    gamma_boost: float = 1.5,
) -> Tuple[np.ndarray, np.ndarray]:
    """Segment deep shadow regions and apply smooth local gamma illumination recovery.

    Returns:
        Tuple of (compensated_bgr, shadow_mask)
    """
    if img_bgr is None or img_bgr.size == 0:
        raise ValueError("Invalid input image")

    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    # Detect shadows in low L* regions
    shadow_mask = np.zeros_like(l_channel, dtype=np.uint8)
    shadow_mask[l_channel < shadow_luminance_threshold] = 255

    # Gaussian blur the shadow mask for feathering / smooth boundary transition
    feathered_mask = cv2.GaussianBlur(shadow_mask, (21, 21), 0).astype(np.float32) / 255.0

    # Gamma correction table for shadow recovery
    inv_gamma = 1.0 / max(0.5, gamma_boost)
    lut = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype(np.uint8)
    l_boosted = cv2.LUT(l_channel, lut)

    # Blend original and boosted luminance using feathered mask
    l_compensated = (
        (feathered_mask * l_boosted) + ((1.0 - feathered_mask) * l_channel)
    ).astype(np.uint8)

    lab_compensated = cv2.merge((l_compensated, a_channel, b_channel))
    return cv2.cvtColor(lab_compensated, cv2.COLOR_LAB2BGR), shadow_mask


def estimate_scene_illumination_stats(img_bgr: np.ndarray) -> Dict[str, float]:
    """Compute illumination statistics including mean L*, contrast ratio, and shadow area."""
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l_channel = lab[:, :, 0]

    mean_l = float(np.mean(l_channel))
    std_l = float(np.std(l_channel))
    shadow_fraction = float(np.sum(l_channel < 50.0)) / float(l_channel.size)

    return {
        "mean_luminance": round(mean_l, 2),
        "luminance_std": round(std_l, 2),
        "shadow_fraction": round(shadow_fraction, 4),
    }

