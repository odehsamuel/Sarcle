"""Attester A: Classical CV Vegetation Analyzer for Metric 1 (green_cover_exg).

Zero machine learning, zero pretrained weights.
Excess Green (ExG) index on chromaticity-normalized channels with bounded Otsu threshold.
"""

import hashlib
import json
from typing import Dict, List, Tuple
import cv2
import numpy as np

ALGORITHM_ID = "green_cover_exg"
ALGORITHM_VERSION = "1.0.0"

DEFAULT_PARAMS = {
    "algorithm_id": ALGORITHM_ID,
    "algorithm_version": ALGORITHM_VERSION,
    "morph_kernel_size": 3,
    "otsu_max": 0.35,
    "otsu_min": 0.05,
    "white_balance": "gray_world",
}


def compute_analyzer_hash(params: Dict = None) -> bytes:
    """Compute deterministic SHA-256 digest of canonical configuration JSON."""
    if params is None:
        params = DEFAULT_PARAMS
    canonical_json = json.dumps(params, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).digest()


def apply_gray_world(img_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Apply gray-world white balance calibrated strictly inside the ROI."""
    roi_pixels = img_bgr[mask > 0]
    if len(roi_pixels) == 0:
        return img_bgr

    mean_b = np.mean(roi_pixels[:, 0]) + 1e-5
    mean_g = np.mean(roi_pixels[:, 1]) + 1e-5
    mean_r = np.mean(roi_pixels[:, 2]) + 1e-5
    mean_gray = (mean_b + mean_g + mean_r) / 3.0

    balanced = img_bgr.astype(np.float32)
    balanced[:, :, 0] *= mean_gray / mean_b
    balanced[:, :, 1] *= mean_gray / mean_g
    balanced[:, :, 2] *= mean_gray / mean_r

    return np.clip(balanced, 0, 255).astype(np.uint8)


def analyze_green_cover(
    jpeg_bytes: bytes,
    roi_points: List[Dict[str, float]],
    params: Dict = None,
) -> Tuple[int, np.ndarray, bytes]:
    """Compute green vegetation cover in basis points (0..10000).

    Returns:
        (cover_bps, binary_vegetation_mask, analyzer_hash)
    """
    if params is None:
        params = DEFAULT_PARAMS

    analyzer_hash = compute_analyzer_hash(params)

    # Decode JPEG
    nparr = np.frombuffer(jpeg_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise ValueError("Failed to decode JPEG bytes")

    height, width, _ = img_bgr.shape

    # Construct ROI polygon mask
    pts = np.array(
        [[int(p["x"] * width), int(p["y"] * height)] for p in roi_points],
        dtype=np.int32,
    )
    roi_mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillPoly(roi_mask, [pts], 255)
    total_roi_pixels = cv2.countNonZero(roi_mask)
    if total_roi_pixels == 0:
        raise ValueError("Degenerate ROI polygon with 0 pixels")

    # Optional Gray-world white balance
    if params.get("white_balance") == "gray_world":
        img_proc = apply_gray_world(img_bgr, roi_mask)
    else:
        img_proc = img_bgr

    # Convert to float and compute chromaticity-normalized channels
    # Note: OpenCV is BGR
    b = img_proc[:, :, 0].astype(np.float32)
    g = img_proc[:, :, 1].astype(np.float32)
    r = img_proc[:, :, 2].astype(np.float32)

    total_intensity = r + g + b + 1e-6
    r_norm = r / total_intensity
    g_norm = g / total_intensity
    b_norm = b / total_intensity

    # Excess Green index (ExG): ExG = 2*g - r - b
    exg = 2.0 * g_norm - r_norm - b_norm

    # Isolate ROI values
    roi_exg = exg[roi_mask > 0]

    # Map ExG (typically -1.0 to 2.0) into 8-bit unsigned range for Otsu
    # Green pixels usually have ExG > 0
    exg_shifted = np.clip((roi_exg + 1.0) / 3.0 * 255.0, 0, 255).astype(np.uint8)

    # Otsu thresholding
    otsu_thresh_raw, _ = cv2.threshold(
        exg_shifted, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    otsu_val = (otsu_thresh_raw / 255.0) * 3.0 - 1.0  # Convert back to ExG scale

    # Clamp Otsu threshold to configurable bounds
    clamped_thresh = float(
        np.clip(otsu_val, params["otsu_min"], params["otsu_max"])
    )

    # Generate binary vegetation mask within ROI
    veg_mask = np.zeros((height, width), dtype=np.uint8)
    veg_mask[(exg > clamped_thresh) & (roi_mask > 0)] = 255

    # Morphological opening (remove noise specks)
    k_size = params.get("morph_kernel_size", 3)
    if k_size > 1:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_size, k_size))
        veg_mask = cv2.morphologyEx(veg_mask, cv2.MORPH_OPEN, kernel)
        veg_mask = cv2.bitwise_and(veg_mask, veg_mask, mask=roi_mask)

    veg_pixel_count = cv2.countNonZero(veg_mask)
    cover_bps = int(round((veg_pixel_count / total_roi_pixels) * 10000.0))
    cover_bps = int(np.clip(cover_bps, 0, 10000))

    return cover_bps, veg_mask, analyzer_hash
