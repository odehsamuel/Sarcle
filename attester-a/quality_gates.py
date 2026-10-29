"""Quality Gates for Attester A.

Enforces physical and optical sanity checks before evidence is accepted:
1. Exposure bounds (reject underexposed or overexposed frames)
2. Blur estimation (variance of Laplacian)
3. Camera displacement / movement detection (ORB feature matching & RANSAC homography)
"""

from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np


class QualityGateFailure(Exception):
    def __init__(self, reason: str, details: Dict):
        super().__init__(reason)
        self.reason = reason
        self.details = details


def check_exposure(
    img_bgr: np.ndarray,
    roi_mask: np.ndarray,
    min_luminance: float = 40.0,
    max_luminance: float = 220.0,
):
    """Ensure illumination inside the ROI is within acceptable dynamic range."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    roi_pixels = gray[roi_mask > 0]
    if len(roi_pixels) == 0:
        raise QualityGateFailure(
            "EMPTY_ROI", {"message": "ROI contains zero pixels"}
        )

    mean_lum = float(np.mean(roi_pixels))
    if mean_lum < min_luminance:
        raise QualityGateFailure(
            "FRAME_UNDEREXPOSED",
            {
                "mean_luminance": mean_lum,
                "min_permitted": min_luminance,
                "message": "Scene is too dark for reliable vegetation analysis",
            },
        )
    if mean_lum > max_luminance:
        raise QualityGateFailure(
            "FRAME_OVEREXPOSED",
            {
                "mean_luminance": mean_lum,
                "max_permitted": max_luminance,
                "message": "Scene is washed out / overexposed",
            },
        )


def check_blur(img_bgr: np.ndarray, min_variance: float = 50.0):
    """Check focus sharpness using variance of the Laplacian operator."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    if laplacian_var < min_variance:
        raise QualityGateFailure(
            "FRAME_TOO_BLURRY",
            {
                "laplacian_variance": laplacian_var,
                "min_permitted": min_variance,
                "message": "Frame lacks sufficient high-frequency edge detail",
            },
        )


def check_camera_movement(
    curr_bgr: np.ndarray,
    prev_bgr: np.ndarray,
    min_inlier_ratio: float = 0.70,
    min_matches: int = 15,
    max_pixel_drift: float = 20.0,
):
    """Detect camera physical displacement using ORB feature alignment and RANSAC homography."""
    gray_curr = cv2.cvtColor(curr_bgr, cv2.COLOR_BGR2GRAY)
    gray_prev = cv2.cvtColor(prev_bgr, cv2.COLOR_BGR2GRAY)

    orb = cv2.ORB_create(nfeatures=1000)
    kp_prev, des_prev = orb.detectAndCompute(gray_prev, None)
    kp_curr, des_curr = orb.detectAndCompute(gray_curr, None)

    if (
        des_prev is None
        or des_curr is None
        or len(kp_prev) < min_matches
        or len(kp_curr) < min_matches
    ):
        raise QualityGateFailure(
            "CAMERA_ALIGNMENT_INSUFFICIENT_FEATURES",
            {
                "features_prev": len(kp_prev) if kp_prev else 0,
                "features_curr": len(kp_curr) if kp_curr else 0,
                "message": "Not enough distinctive visual landmarks to verify camera stillness",
            },
        )

    # Brute-force matcher with Hamming distance for binary descriptors
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(des_prev, des_curr)

    if len(matches) < min_matches:
        raise QualityGateFailure(
            "CAMERA_MOVED_FEW_MATCHES",
            {
                "matches": len(matches),
                "required": min_matches,
                "message": "Frames are too visually dissimilar",
            },
        )

    pts_prev = np.float32(
        [kp_prev[m.queryIdx].pt for m in matches]
    ).reshape(-1, 1, 2)
    pts_curr = np.float32(
        [kp_curr[m.trainIdx].pt for m in matches]
    ).reshape(-1, 1, 2)

    # Find homography using RANSAC
    H, inlier_mask = cv2.findHomography(pts_prev, pts_curr, cv2.RANSAC, 5.0)
    if inlier_mask is None or H is None:
        raise QualityGateFailure(
            "CAMERA_MOVED",
            {
                "inlier_ratio": 0.0,
                "message": "Geometric homography calculation failed",
            },
        )

    inliers = int(np.sum(inlier_mask))
    inlier_ratio = float(inliers / len(matches))

    if inlier_ratio < min_inlier_ratio:
        raise QualityGateFailure(
            "CAMERA_MOVED",
            {
                "inlier_ratio": inlier_ratio,
                "threshold": min_inlier_ratio,
                "inliers": inliers,
                "total_matches": len(matches),
                "message": "Inlier match ratio fell below tolerance",
            },
        )

    # Check physical translation drift from identity
    dx = float(H[0, 2])
    dy = float(H[1, 2])
    drift = float(np.sqrt(dx * dx + dy * dy))
    if drift > max_pixel_drift:
        raise QualityGateFailure(
            "CAMERA_MOVED",
            {
                "pixel_drift": drift,
                "max_drift_permitted": max_pixel_drift,
                "dx": dx,
                "dy": dy,
                "message": f"Camera shifted by {drift:.1f} pixels between captures",
            },
        )


def run_quality_gates(
    curr_jpeg: bytes,
    roi_points: List[Dict[str, float]],
    prev_jpeg: Optional[bytes] = None,
    min_inlier_ratio: float = 0.70,
):
    """Execute all quality gates on an incoming frame."""
    nparr = np.frombuffer(curr_jpeg, np.uint8)
    curr_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if curr_bgr is None:
        raise QualityGateFailure("CORRUPT_JPEG", {"message": "Invalid JPEG bitstream"})

    height, width, _ = curr_bgr.shape
    pts = np.array(
        [[int(p["x"] * width), int(p["y"] * height)] for p in roi_points],
        dtype=np.int32,
    )
    roi_mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillPoly(roi_mask, [pts], 255)

    # Gate 1: Exposure
    check_exposure(curr_bgr, roi_mask)

    # Gate 2: Blur
    check_blur(curr_bgr)

    # Gate 3: Camera movement if prior observation exists
    if prev_jpeg is not None:
        prev_arr = np.frombuffer(prev_jpeg, np.uint8)
        prev_bgr = cv2.imdecode(prev_arr, cv2.IMREAD_COLOR)
        if prev_bgr is not None:
            check_camera_movement(
                curr_bgr, prev_bgr, min_inlier_ratio=min_inlier_ratio
            )
