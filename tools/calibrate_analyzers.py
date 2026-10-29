"""Calibration and agreement benchmark across Analyzer A (ExG) and Analyzer B (CIELAB a*).

Tests agreement across 50 procedural synthetic field scenes:
- Baseline high-vegetation scenes (50-80% cover)
- Mid-clearing scenes (20-40% cover)
- Cleared completion scenes (2-15% cover)
- Various lighting and noise conditions

Documents divergence distribution and why JPEG compression / colorspace conversion
mandates a tolerance (max_divergence_bps).
"""

import json
import os
import sys
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "attester-a"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "attester-b"))
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "tools", "synthetic-scenes")
)

from analyzer import analyze_green_cover
from analyzer_b import analyze_cielab_cover
from generate import generate_scene


def run_calibration(num_scenes: int = 50, output_path: str = None) -> dict:
    print(
        f"=== Running Calibration Benchmark across {num_scenes} Synthetic Scenes ==="
    )

    roi_points = [
        {"x": 0.1500, "y": 0.2000},
        {"x": 0.8500, "y": 0.2000},
        {"x": 0.8500, "y": 0.8000},
        {"x": 0.1500, "y": 0.8000},
    ]

    target_covers = [
        # 15 Baseline high-cover scenes
        *[int(x) for x in np.linspace(5000, 8000, 15)],
        # 15 Mid-clearing scenes
        *[int(x) for x in np.linspace(2000, 4500, 15)],
        # 20 Cleared completion scenes
        *[int(x) for x in np.linspace(300, 1800, 20)],
    ]

    divergences = []
    results = []

    for i, target_bps in enumerate(target_covers[:num_scenes]):
        seed = 1000 + i
        exposure = 0.85 + (i % 5) * 0.08  # Exposure between 0.85 and 1.17
        noise = 0.01 * (i % 3)

        jpeg_bytes, _, gt_bps = generate_scene(
            target_cover_bps=target_bps,
            roi_points=roi_points,
            seed=seed,
            exposure_multiplier=exposure,
            noise_level=noise,
        )

        bps_a, _, _ = analyze_green_cover(jpeg_bytes, roi_points)
        bps_b, _ = analyze_cielab_cover(jpeg_bytes, roi_points)

        diff = abs(bps_a - bps_b)
        divergences.append(diff)

        results.append(
            {
                "scene_idx": i + 1,
                "target_bps": target_bps,
                "ground_truth_bps": gt_bps,
                "analyzer_a_exg_bps": bps_a,
                "analyzer_b_cielab_bps": bps_b,
                "divergence_bps": diff,
            }
        )

    divergences = np.array(divergences)
    stats = {
        "num_scenes": len(divergences),
        "mean_divergence_bps": float(np.mean(divergences)),
        "median_divergence_bps": float(np.median(divergences)),
        "max_divergence_bps": int(np.max(divergences)),
        "percentile_95_bps": float(np.percentile(divergences, 95)),
        "percentile_99_bps": float(np.percentile(divergences, 99)),
        "max_permitted_by_protocol": 500,
        "all_within_tolerance": bool(np.max(divergences) <= 500),
    }

    print(f"Calibration Complete:")
    print(f"  Mean Divergence:   {stats['mean_divergence_bps']:.1f} bps")
    print(f"  Median Divergence: {stats['median_divergence_bps']:.1f} bps")
    print(f"  95th Percentile:   {stats['percentile_95_bps']:.1f} bps")
    print(f"  Max Divergence:    {stats['max_divergence_bps']} bps")
    print(f"  Protocol Limit:    {stats['max_permitted_by_protocol']} bps")
    print(f"  All Passed:        {stats['all_within_tolerance']}")

    summary = {
        "calibration_metadata": {
            "synthetic_only": True,
            "justification": "Tolerance is necessary because DCT quantization in JPEG decoders, integer rounding, and differing colorimetric transformations (chromaticity ExG vs CIELAB fixed-point a*) introduce minor boundary variances on sub-pixel vegetation edges.",
        },
        "statistics": stats,
        "sample_scenes": results[:10],
    }

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(f"Saved calibration report to {output_path}")

    return summary


if __name__ == "__main__":
    out_file = os.path.join(
        os.path.dirname(__file__), "..", "docs", "calibration-report.json"
    )
    run_calibration(num_scenes=50, output_path=out_file)

