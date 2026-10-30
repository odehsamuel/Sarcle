"""Environmental Quality Gate 2: Solar Glare, Flare & Specular Reflection Gate.

Detects direct sun exposure clipping, specular reflections from water puddles,
and lens flare streaks that wash out green vegetation pixels inside the ROI.
"""

from typing import Dict, Optional
import cv2
import numpy as np

try:
    from quality_gates import QualityGateFailure
except ImportError:
    class QualityGateFailure(Exception):
        def __init__(self, reason: str, details: Dict):
            super().__init__(reason)
            self.reason = reason
            self.details = details


def check_solar_glare_and_reflections(
    img_bgr: np.ndarray,
    roi_mask: Optional[np.ndarray] = None,
    max_glare_fraction: float = 0.05,
    saturation_threshold: int = 250,
) -> Dict[str, any]:
    """Inspect frame for specular highlights, sun flare washout, and channel clipping.

    Raises:
        QualityGateFailure: If glare fraction exceeds allowable limits inside the ROI.
    """
    if img_bgr is None or img_bgr.size == 0:
        raise QualityGateFailure("INVALID_IMAGE", {"message": "Image buffer is empty"})

    h, w = img_bgr.shape[:2]
    if roi_mask is None:
        roi_mask = np.ones((h, w), dtype=np.uint8)

    # A pixel is considered clipped / glare if all 3 BGR channels exceed the saturation threshold
    b, g, r = cv2.split(img_bgr)
    glare_mask = (b >= saturation_threshold) & (g >= saturation_threshold) & (r >= saturation_threshold)

    # Restrict analysis to ROI
    roi_glare_pixels = np.sum(glare_mask & (roi_mask > 0))
    total_roi_pixels = np.sum(roi_mask > 0)

    if total_roi_pixels == 0:
        raise QualityGateFailure("EMPTY_ROI", {"message": "ROI contains zero pixels"})

    glare_fraction = float(roi_glare_pixels) / float(total_roi_pixels)

    # Detect high-intensity flare streaks (connected components spanning > 20% frame dimension)
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        glare_mask.astype(np.uint8), connectivity=8
    )

    flare_streak_detected = False
    for i in range(1, num_labels):
        comp_w = stats[i, cv2.CC_STAT_WIDTH]
        comp_h = stats[i, cv2.CC_STAT_HEIGHT]
        if comp_w > 0.25 * w or comp_h > 0.25 * h:
            flare_streak_detected = True
            break

    report = {
        "glare_pixel_count": int(roi_glare_pixels),
        "total_roi_pixels": int(total_roi_pixels),
        "glare_fraction": round(glare_fraction, 4),
        "max_permitted_glare_fraction": max_glare_fraction,
        "flare_streak_detected": flare_streak_detected,
        "glare_exceeded": glare_fraction > max_glare_fraction,
    }

    if report["glare_exceeded"] or (flare_streak_detected and glare_fraction > 0.02):
        raise QualityGateFailure(
            "ERR_SOLAR_GLARE",
            {
                "message": "Solar flare or specular reflection washes out vegetation ROI",
                **report,
            },
        )

    return report

