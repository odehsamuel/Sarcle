"""Lighting-Invariant Feature Matching & Homography Validation Engine.

Aligns observation frames across multi-week epochs (Baseline t0, Completion t1, Follow-up t2)
despite diurnal solar shifts, cloud shadows, and minor camera post deflection.
"""

import math
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np


class FrameAlignmentError(Exception):
    def __init__(self, reason: str, details: Dict):
        super().__init__(reason)
        self.reason = reason
        self.details = details


def preprocess_for_feature_extraction(img_bgr: np.ndarray) -> np.ndarray:
    """Preprocess image with CLAHE on luminance to eliminate lighting gradients."""
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l_eq = clahe.apply(l)
    return l_eq


def compute_frame_homography(
    ref_bgr: np.ndarray,
    target_bgr: np.ndarray,
    max_translation_px: float = 35.0,
    max_rotation_deg: float = 6.0,
    min_inliers: int = 15,
) -> Tuple[np.ndarray, Dict[str, any]]:
    """Compute and validate robust 3x3 homography matrix between reference and target frames.

    Returns:
        Tuple of (H_matrix_3x3, diagnostic_metrics_dict)
    """
    ref_gray = preprocess_for_feature_extraction(ref_bgr)
    tgt_gray = preprocess_for_feature_extraction(target_bgr)

    # Use ORB feature detector with illumination-normalized inputs
    detector = cv2.ORB_create(nfeatures=1500, scaleFactor=1.2, nlevels=8)

    kp1, desc1 = detector.detectAndCompute(ref_gray, None)
    kp2, desc2 = detector.detectAndCompute(tgt_gray, None)

    if desc1 is None or desc2 is None or len(kp1) < min_inliers or len(kp2) < min_inliers:
        raise FrameAlignmentError(
            "INSUFFICIENT_KEYPOINTS",
            {"ref_keypoints": len(kp1) if kp1 else 0, "tgt_keypoints": len(kp2) if kp2 else 0},
        )

    # Match using Hamming distance with k-NN (k=2)
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    matches = matcher.knnMatch(desc1, desc2, k=2)

    # Lowe's ratio test
    good_matches = []
    for m, n in matches:
        if m.distance < 0.75 * n.distance:
            good_matches.append(m)

    if len(good_matches) < min_inliers:
        raise FrameAlignmentError(
            "INSUFFICIENT_MATCHES",
            {"good_matches": len(good_matches), "min_required": min_inliers},
        )

    src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

    H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 3.0)
    if H is None:
        raise FrameAlignmentError("HOMOGRAPHY_RANSAC_FAILED", {"matches_used": len(good_matches)})

    inliers = int(np.sum(mask)) if mask is not None else 0
    inlier_ratio = float(inliers) / float(len(good_matches))

    # Decompose homography parameters
    # Translation: tx = H[0, 2], ty = H[1, 2]
    tx = float(H[0, 2])
    ty = float(H[1, 2])
    translation_disp = math.sqrt(tx * tx + ty * ty)

    # Rotation angle: theta = atan2(H[1, 0], H[0, 0])
    rotation_rad = math.atan2(H[1, 0], H[0, 0])
    rotation_deg = abs(math.degrees(rotation_rad))

    # Determinant check (scale / inversion sanity)
    det = float(np.linalg.det(H[:2, :2]))

    report = {
        "inliers": inliers,
        "inlier_ratio": round(inlier_ratio, 3),
        "translation_px": round(translation_disp, 2),
        "rotation_deg": round(rotation_deg, 2),
        "scale_determinant": round(det, 3),
        "h_matrix": H.tolist(),
    }

    if translation_disp > max_translation_px:
        raise FrameAlignmentError(
            "EXCESSIVE_CAMERA_DISPLACEMENT",
            {"message": f"Camera translated {translation_disp:.1f}px (limit: {max_translation_px}px)", **report},
        )

    if rotation_deg > max_rotation_deg:
        raise FrameAlignmentError(
            "EXCESSIVE_CAMERA_ROTATION",
            {"message": f"Camera rotated {rotation_deg:.1f}deg (limit: {max_rotation_deg}deg)", **report},
        )

    if not (0.80 <= det <= 1.25):
        raise FrameAlignmentError(
            "UNSTABLE_GEOMETRIC_SCALE",
            {"message": f"Scale determinant {det:.2f} outside safe [0.80, 1.25] bounds", **report},
        )

    return H, report


def warp_roi_polygon(roi_points: List[Tuple[float, float]], H: np.ndarray) -> List[Tuple[float, float]]:
    """Transform normalized polygon coordinates (0..1) through homography H."""
    pts = np.array(roi_points, dtype=np.float32).reshape(-1, 1, 2)
    warped = cv2.perspectiveTransform(pts, H)
    return [(float(p[0, 0]), float(p[0, 1])) for p in warped]
