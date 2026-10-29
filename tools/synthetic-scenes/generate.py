"""Clean-room procedural synthetic scene generator.

Zero third-party datasets or pretrained weights.
Generates synthetic agricultural field textures with known ground-truth green cover.
"""

import io
import json
import math
import os
import random
from typing import Dict, List, Tuple
import cv2
import numpy as np
from PIL import Image, ImageDraw


def generate_soil_texture(
    width: int = 640, height: int = 480, seed: int = 42
) -> np.ndarray:
    """Generate realistic synthetic soil substrate using multiscale procedural noise."""
    np.random.seed(seed)
    # Base earthy brown: RGB ~(115, 85, 60)
    base_color = np.array([60, 85, 115], dtype=np.float32)  # BGR for OpenCV

    noise_low = cv2.resize(
        np.random.normal(0, 15, (height // 16, width // 16)).astype(np.float32),
        (width, height),
        interpolation=cv2.INTER_CUBIC,
    )
    noise_med = cv2.resize(
        np.random.normal(0, 10, (height // 4, width // 4)).astype(np.float32),
        (width, height),
        interpolation=cv2.INTER_CUBIC,
    )
    noise_high = np.random.normal(0, 6, (height, width)).astype(np.float32)

    total_noise = noise_low + noise_med + noise_high

    soil = np.zeros((height, width, 3), dtype=np.float32)
    soil[:, :, 0] = base_color[0] + total_noise * 0.8  # B
    soil[:, :, 1] = base_color[1] + total_noise * 0.9  # G
    soil[:, :, 2] = base_color[2] + total_noise * 1.1  # R

    return np.clip(soil, 20, 240).astype(np.uint8)


def get_roi_mask(
    width: int, height: int, roi_points: List[Dict[str, float]]
) -> np.ndarray:
    """Render a binary mask for the canonical polygon ROI."""
    pts = np.array(
        [[int(p["x"] * width), int(p["y"] * height)] for p in roi_points],
        dtype=np.int32,
    )
    mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillPoly(mask, [pts], 255)
    return mask


def generate_scene(
    width: int = 640,
    height: int = 480,
    target_cover_bps: int = 6000,
    roi_points: List[Dict[str, float]] = None,
    seed: int = 100,
    noise_level: float = 0.0,
    blur_kernel: int = 0,
    exposure_multiplier: float = 1.0,
    dx: int = 0,
    dy: int = 0,
) -> Tuple[bytes, np.ndarray, int]:
    """Generate a synthetic scene frame with procedural vegetation patches.

    Returns:
        (jpeg_bytes, ground_truth_mask, exact_ground_truth_bps)
    """
    random.seed(seed)
    np.random.seed(seed)

    if roi_points is None:
        roi_points = [
            {"x": 0.1500, "y": 0.2000},
            {"x": 0.8500, "y": 0.2000},
            {"x": 0.8500, "y": 0.8000},
            {"x": 0.1500, "y": 0.8000},
        ]

    soil = generate_soil_texture(width, height, seed=seed)
    roi_mask = get_roi_mask(width, height, roi_points)
    roi_pixel_count = cv2.countNonZero(roi_mask)

    target_vegetation_pixels = int(roi_pixel_count * (target_cover_bps / 10000.0))

    # Binary mask for procedural vegetation
    veg_mask = np.zeros((height, width), dtype=np.uint8)

    # Spawn clustered elliptical weed patches until target cover is reached
    # Min/max bounding box of ROI
    xs = [int(p["x"] * width) for p in roi_points]
    ys = [int(p["y"] * height) for p in roi_points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    current_pixels = 0
    attempts = 0
    max_attempts = 5000

    while (
        current_pixels < target_vegetation_pixels and attempts < max_attempts
    ):
        attempts += 1
        cx = random.randint(min_x, max_x)
        cy = random.randint(min_y, max_y)
        if roi_mask[cy, cx] == 0:
            continue

        rx = random.randint(8, 30)
        ry = random.randint(8, 30)
        angle = random.randint(0, 180)

        patch = np.zeros((height, width), dtype=np.uint8)
        cv2.ellipse(patch, (cx, cy), (rx, ry), angle, 0, 360, 255, -1)
        patch = cv2.bitwise_and(patch, patch, mask=roi_mask)

        # Check if adding this patch overshoots target by too much
        combined = cv2.bitwise_or(veg_mask, patch)
        new_count = cv2.countNonZero(combined)
        if new_count <= target_vegetation_pixels + 50:
            veg_mask = combined
            current_pixels = new_count
        elif target_vegetation_pixels - current_pixels < 50:
            break

    # Colorize vegetation with healthy plant green: BGR ~(35, 140, 50)
    veg_color_base = np.array([35, 140, 50], dtype=np.float32)
    plant_layer = np.zeros_like(soil, dtype=np.float32)
    veg_noise = np.random.normal(0, 12, (height, width, 3)).astype(np.float32)
    plant_layer[:, :] = veg_color_base + veg_noise

    # Blend vegetation onto soil using veg_mask
    mask_3d = np.repeat(veg_mask[:, :, np.newaxis], 3, axis=2) / 255.0
    composite = (
        plant_layer * mask_3d + soil.astype(np.float32) * (1.0 - mask_3d)
    )

    # Apply camera displacement if specified
    if dx != 0 or dy != 0:
        M = np.float32([[1, 0, dx], [0, 1, dy]])
        composite = cv2.warpAffine(composite, M, (width, height))
        veg_mask = cv2.warpAffine(veg_mask, M, (width, height))
        roi_mask = cv2.warpAffine(roi_mask, M, (width, height))

    # Apply sensor noise
    if noise_level > 0:
        noise = np.random.normal(0, noise_level * 255, composite.shape)
        composite = np.clip(composite + noise, 0, 255)

    # Apply blur
    if blur_kernel > 1:
        if blur_kernel % 2 == 0:
            blur_kernel += 1
        composite = cv2.GaussianBlur(composite, (blur_kernel, blur_kernel), 0)

    # Apply lighting/exposure multiplier
    if exposure_multiplier != 1.0:
        composite = np.clip(composite * exposure_multiplier, 0, 255)

    result_img = np.clip(composite, 0, 255).astype(np.uint8)

    # Encode to JPEG
    _, enc = cv2.imencode(".jpg", result_img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    jpeg_bytes = enc.tobytes()

    # Exact measured ground truth basis points
    effective_roi = cv2.countNonZero(roi_mask)
    exact_gt_pixels = cv2.countNonZero(
        cv2.bitwise_and(veg_mask, veg_mask, mask=roi_mask)
    )
    exact_bps = (
        int(round((exact_gt_pixels / effective_roi) * 10000))
        if effective_roi > 0
        else 0
    )

    return jpeg_bytes, veg_mask, exact_bps


if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "sample_output")
    os.makedirs(out_dir, exist_ok=True)
    jpeg_b, mask_b, bps_b = generate_scene(
        target_cover_bps=6500, seed=1, exposure_multiplier=1.0
    )
    jpeg_c, mask_c, bps_c = generate_scene(
        target_cover_bps=800, seed=2, exposure_multiplier=1.0
    )
    with open(os.path.join(out_dir, "baseline_sample.jpg"), "wb") as f:
        f.write(jpeg_b)
    with open(os.path.join(out_dir, "completion_sample.jpg"), "wb") as f:
        f.write(jpeg_c)
    print(f"Generated sample synthetic baseline: {bps_b} bps")
    print(f"Generated sample synthetic completion: {bps_c} bps")
