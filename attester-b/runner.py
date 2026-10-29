"""Attester B runner service.

Runs with its own distinct Stellar keypair.
Listens for or is invoked on new observations to compute Analysis B
and submit add_analysis to the evidence_registry contract.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

from analyzer_b import analyze_cielab_cover, compute_analyzer_b_hash
from chain_client import ChainClient


class AttesterBRunner:
    def __init__(
        self,
        chain: ChainClient,
        attester_addr: str = "G_ATTESTER_B_RUST",
        threshold: int = -50,
    ):
        self.chain = chain
        self.attester_addr = attester_addr
        self.threshold = threshold
        self.analyzer_hash = compute_analyzer_b_hash(threshold)

    def process_and_submit(
        self, obs_id: int, image_bytes: bytes, roi_points: list
    ) -> int:
        """Compute CIELAB cover and submit add_analysis to evidence_registry."""
        cover_bps, an_hash = analyze_cielab_cover(
            image_bytes, roi_points, threshold=self.threshold
        )
        self.chain.add_analysis(
            attester_addr=self.attester_addr,
            obs_id=obs_id,
            analyzer_hash=an_hash,
            value_bps=cover_bps,
        )
        return cover_bps

