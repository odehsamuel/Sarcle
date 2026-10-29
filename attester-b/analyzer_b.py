"""Attester B: Python reference implementation of Rust CIELAB fixed-point analyzer.

Family 2 analyzer for Metric 1.
Computes vegetation cover by integer thresholding on the CIELAB a* channel.
"""

import hashlib
import json
from typing import Dict, List, Tuple
import cv2
import numpy as np

ALGORITHM_ID = "cielab_fixed_point"
VERSION = "1.0.0"
DEFAULT_THRESHOLD = -50


def compute_analyzer_b_hash(threshold: int = DEFAULT_THRESHOLD) -> bytes:
    canonical = json.dumps(
        {
            "algorithm_id": ALGORITHM_ID,
            "threshold": threshold,
            "version": VERSION,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).digest()


def srgb_to_cielab_a_fixed_matrix(img_rgb: np.ndarray) -> np.ndarray:
    """Fixed-point integer matrix operation approximating CIELAB a* channel."""
    r = img_rgb[:, :, 0].astype(np.int32)
    g = img_rgb[:, :, 1].astype(np.int32)
    b = img_rgb[:, :, 2].astype(np.int32)

    # Approximate XYZ coordinates scaled by 1024
    x_scaled = (422 * r + 366 * g + 185 * b) >> 10
    y_scaled = (218 * r + 732 * g + 74 * b) >> 10

    # a* = 500 * (f(X) - f(Y))
    diff = x_scaled - y_scaled
    a_star = (diff * 500) >> 8
    return a_star


def analyze_cielab_cover(
    jpeg_bytes: bytes,
    roi_points: List[Dict[str, float]],
    threshold: int = DEFAULT_THRESHOLD,
) -> Tuple[int, bytes]:
    """Compute vegetation cover via CIELAB a* fixed-point thresholding.

    Returns:
        (cover_bps, analyzer_hash)
    """
    nparr = np.frombuffer(jpeg_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise ValueError("Failed to decode JPEG")

    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    height, width, _ = img_rgb.shape

    pts = np.array(
        [[int(p["x"] * width), int(p["y"] * height)] for p in roi_points],
        dtype=np.int32,
    )
    roi_mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillPoly(roi_mask, [pts], 255)
    total_roi = cv2.countNonZero(roi_mask)
    if total_roi == 0:
        return 0, compute_analyzer_b_hash(threshold)

    a_star = srgb_to_cielab_a_fixed_matrix(img_rgb)
    veg_mask = (a_star < threshold) & (roi_mask > 0)
    veg_count = int(np.sum(veg_mask))

    cover_bps = int(round((veg_count / total_roi) * 10000.0))
    cover_bps = int(np.clip(cover_bps, 0, 10000))

    return cover_bps, compute_analyzer_b_hash(threshold)
