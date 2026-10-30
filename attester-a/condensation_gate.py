"""Environmental Quality Gate 1: Lens Condensation, Droplet & Defocus Detection Filter.

Detects internal glass fogging, dew accumulation, and external rain droplet lensing
before submitting frames to vegetation analyzers.
"""

from typing import Dict
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


def check_condensation_and_droplets(
    img_bgr: np.ndarray,
    min_laplacian_var: float = 45.0,
    max_droplet_anomalies: int = 6,
) -> Dict[str, any]:
    """Inspect frame for optical condensation, fogging, and droplet refraction.

    Raises:
        QualityGateFailure: If fogging or droplet contamination is detected.
    """
    if img_bgr is None or img_bgr.size == 0:
        raise QualityGateFailure("INVALID_IMAGE", {"message": "Image buffer is empty"})

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # 1. Laplacian sharpness check (condensation causes severe edge blur)
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    # 2. Local gradient standard deviation (droplets cause sharp isolated circular rings)
    # Detect potential droplet lensing using blurred gradient difference
    blurred = cv2.GaussianBlur(gray, (9, 9), 2.0)
    high_freq = cv2.absdiff(gray, blurred)
    droplet_mask = high_freq > 40

    # Count connected components representing isolated refraction spots
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        droplet_mask.astype(np.uint8), connectivity=8
    )

    # Filter out tiny noise: droplets typically span 20 to 1000 pixels
    droplet_count = 0
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        if 20 <= area <= 1500:
            droplet_count += 1

    report = {
        "laplacian_variance": round(laplacian_var, 2),
        "min_permitted_laplacian": min_laplacian_var,
        "droplet_anomalies_detected": droplet_count,
        "max_permitted_droplets": max_droplet_anomalies,
        "fog_detected": laplacian_var < min_laplacian_var,
        "droplets_detected": droplet_count > max_droplet_anomalies,
    }

    if report["fog_detected"]:
        raise QualityGateFailure(
            "ERR_CONDENSATION_FOG",
            {
                "message": "Lens condensation or severe defocus detected; frame edges attenuated",
                **report,
            },
        )

    if report["droplets_detected"]:
        raise QualityGateFailure(
            "ERR_LENS_DROPLETS",
            {
                "message": "Water droplets or splatter detected on optical aperture",
                **report,
            },
        )

    return report

