"""End-to-End Simulation Script for Proof-of-Weeding.

Executes complete lifecycle with zero hardware:
1. Setup contracts, attesters, devices, and allowlisted analyzers
2. Job Creation (funded escrow)
3. Simulated Baseline Capture & Attestation
4. Job State Progression to BaselineRecorded
5. Simulated Clearing & Completion Capture
6. Dual Attester Analysis & Agreement Check
7. Challenge Window Wait & Finalize Completion (Payout + Retainage Lock)
8. Regrowth Monitoring Window & Follow-up Capture
9. Finalize Follow-up & Full Job Settlement
"""

import hashlib
import json
import logging
import os
import struct
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "attester-a"))
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "tools", "device-simulator")
)
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "tools", "synthetic-scenes")
)

from analyzer import analyze_green_cover, compute_analyzer_hash
from chain_client import ChainClient
from simulate import EdgeDeviceSimulator

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [E2E-SIM] %(message)s"
)
logger = logging.getLogger("e2e-sim")


def run_e2e_simulation():
    logger.info("==================================================")
    logger.info("STARTING PROOF-OF-WEEDING END-TO-END SIMULATION")
    logger.info("==================================================")

    # 1. Setup Environment
    chain = ChainClient(mode="mock")
    admin = chain.admin
    farmer = "G_FARMER_ALICE"
    worker = "G_WORKER_BOB"
    arbiter = "G_ARBITER_CHARLIE"
    attester_a = "G_ATTESTER_A_PYTHON"
    attester_b = "G_ATTESTER_B_RUST"

    # Register Attesters
    chain.registry_mock.add_attester(admin, attester_a)
    chain.registry_mock.add_attester(admin, attester_b)

    # Register Device
    sim = EdgeDeviceSimulator()
    chain.registry_mock.register_device(admin, sim.pk)
    logger.info(f"Registered Device ID: {sim.pk.hex()[:16]}...")

    # Allowlist Analyzers
    an_a_hash = compute_analyzer_hash()  # Python ExG (Family 1)
    chain.registry_mock.allow_analyzer(
        admin, an_a_hash, metric_id=1, family_id=1
    )

    an_b_hash = hashlib.sha256(
        b"cielab_fixed_point_v1"
    ).digest()  # Rust CIELAB (Family 2)
    chain.registry_mock.allow_analyzer(
        admin, an_b_hash, metric_id=1, family_id=2
    )

    # Canonical ROI Polygon
    roi_points = [
        {"x": 0.1500, "y": 0.2000},
        {"x": 0.8500, "y": 0.2000},
        {"x": 0.8500, "y": 0.8000},
        {"x": 0.1500, "y": 0.8000},
    ]
    canonical_roi_json = json.dumps(
        {
            "name": "drainage_ditch_south",
            "points": [
                {"x": f"{p['x']:.4f}", "y": f"{p['y']:.4f}"}
                for p in roi_points
            ],
            "version": 1,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    roi_hash = hashlib.sha256(canonical_roi_json).digest()

    # 2. Farmer creates job in WorkEscrow
    now = chain.registry_mock.current_timestamp
    job_params = {
        "farmer": farmer,
        "worker": worker,
        "token": "C_TESTNET_SAC_TOKEN",
        "amount": 100_000,
        "device_id": sim.pk,
        "roi_hash": roi_hash,
        "metric_id": 1,
        "arbiter": arbiter,
        "threshold_bps": 7500,  # 75% weed cover reduction required
        "min_baseline_bps": 4000,  # At least 40% cover to qualify
        "retainage_bps": 2000,  # 20% retainage held for followup
        "followup_delay_secs": 86400,  # 24 hours
        "max_regrowth_bps": 500,  # 5% max permissible regrowth
        "baseline_deadline": now + 7200,
        "completion_deadline": now + 86400 * 3,
        "followup_deadline": now + 86400 * 10,
        "challenge_window_secs": 3600,
    }
    job_id = chain.escrow_mock.create_job(job_params)
    logger.info(
        f"[STEP 1] Created Job {job_id} in WorkEscrow (Amount: 100,000 tokens, State: Funded)"
    )

    # 3. Baseline Capture & Attestation
    chal_baseline = chain.request_challenge(
        attester_a, job_id, sim.pk, kind=0
    )
    msg_base, sig_base, jpeg_base, gt_base_bps = sim.capture_and_sign(
        job_ref=job_id,
        kind=0,
        target_cover_bps=6500,
        challenge=chal_baseline,
        roi_points=roi_points,
        seed=101,
    )
    img_base_hash = hashlib.sha256(jpeg_base).digest()
    an_a_base_bps, _, _ = analyze_green_cover(jpeg_base, roi_points)

    ts_base = struct.unpack(">Q", msg_base[59:67])[0]
    obs_id_1 = chain.submit_observation(
        attester_addr=attester_a,
        job_ref=job_id,
        kind=0,
        image_hash=img_base_hash,
        roi_hash=roi_hash,
        metric_id=1,
        challenge=chal_baseline,
        counter=sim.counter,
        timestamp=ts_base,
        signature=sig_base,
        analyzer_hash=an_a_hash,
        value_bps=an_a_base_bps,
    )

    # Attester B submits Analysis B
    an_b_base_bps = an_a_base_bps + 80  # Simulating independent analysis B
    chain.add_analysis(attester_b, obs_id_1, an_b_hash, an_b_base_bps)
    obs_1 = chain.get_observation(obs_id_1)
    logger.info(
        f"[STEP 2] Observation 1 (Baseline) Accepted on-chain. Status: {obs_1['status']}, Accepted Cover: {obs_1['accepted_value_bps']} bps"
    )

    # Attach baseline to escrow
    chain.attach_observation(farmer, job_id, obs_id_1)
    job = chain.escrow_mock.get_job(job_id)
    logger.info(
        f"[STEP 3] Attached Baseline to Job {job_id}. State: {job['state']}"
    )

    # 4. Completion Capture & Attestation
    logger.info("Worker completed vegetation clearing in the target zone...")
    chal_comp = chain.request_challenge(attester_a, job_id, sim.pk, kind=1)
    msg_comp, sig_comp, jpeg_comp, _ = sim.capture_and_sign(
        job_ref=job_id,
        kind=1,
        target_cover_bps=900,  # 9% cover remaining
        challenge=chal_comp,
        roi_points=roi_points,
        seed=102,
    )
    img_comp_hash = hashlib.sha256(jpeg_comp).digest()
    an_a_comp_bps, _, _ = analyze_green_cover(jpeg_comp, roi_points)

    ts_comp = struct.unpack(">Q", msg_comp[59:67])[0]
    obs_id_2 = chain.submit_observation(
        attester_addr=attester_a,
        job_ref=job_id,
        kind=1,
        image_hash=img_comp_hash,
        roi_hash=roi_hash,
        metric_id=1,
        challenge=chal_comp,
        counter=sim.counter,
        timestamp=ts_comp,
        signature=sig_comp,
        analyzer_hash=an_a_hash,
        value_bps=an_a_comp_bps,
    )

    # Attester B submits Analysis B
    an_b_comp_bps = an_a_comp_bps + 40
    chain.add_analysis(attester_b, obs_id_2, an_b_hash, an_b_comp_bps)
    obs_2 = chain.get_observation(obs_id_2)
    logger.info(
        f"[STEP 4] Observation 2 (Completion) Accepted on-chain. Cover: {obs_2['accepted_value_bps']} bps"
    )

    # Attach completion to escrow
    chain.attach_observation(worker, job_id, obs_id_2)
    job = chain.escrow_mock.get_job(job_id)
    logger.info(
        f"[STEP 5] Attached Completion to Job {job_id}. State: {job['state']} (Challenge Window Active)"
    )

    # 5. Challenge Window & Finalize Completion
    logger.info("Advancing time past challenge window without dispute...")
    chain.registry_mock.current_timestamp = (
        job["completion_recorded_at"] + job["challenge_window_secs"] + 10
    )
    chain.finalize_completion(job_id)

    job = chain.escrow_mock.get_job(job_id)
    logger.info(
        f"[STEP 6] Finalized Completion! Payout to Worker: {job['paid_to_worker']} tokens. Retained Amount: {job['retained_amount']} tokens. State: {job['state']}"
    )

    # 6. Regrowth Monitoring Window & Follow-up
    logger.info(
        "Advancing time past 24h retention window for regrowth check..."
    )
    chain.registry_mock.current_timestamp += job["followup_delay_secs"] + 60
    now_fol = chain.registry_mock.current_timestamp

    chal_fol = chain.request_challenge(attester_a, job_id, sim.pk, kind=2)
    msg_fol, sig_fol, jpeg_fol, _ = sim.capture_and_sign(
        job_ref=job_id,
        kind=2,
        target_cover_bps=1100,  # 11% cover (only 2% regrowth, well within 5% max_regrowth)
        challenge=chal_fol,
        roi_points=roi_points,
        seed=103,
        timestamp=now_fol,
    )
    img_fol_hash = hashlib.sha256(jpeg_fol).digest()
    an_a_fol_bps, _, _ = analyze_green_cover(jpeg_fol, roi_points)

    obs_id_3 = chain.submit_observation(
        attester_addr=attester_a,
        job_ref=job_id,
        kind=2,
        image_hash=img_fol_hash,
        roi_hash=roi_hash,
        metric_id=1,
        challenge=chal_fol,
        counter=sim.counter,
        timestamp=now_fol,
        signature=sig_fol,
        analyzer_hash=an_a_hash,
        value_bps=an_a_fol_bps,
    )
    chain.add_analysis(attester_b, obs_id_3, an_b_hash, an_a_fol_bps + 30)
    obs_3 = chain.get_observation(obs_id_3)
    logger.info(
        f"[STEP 7] Observation 3 (Follow-up) Accepted on-chain. Regrowth Cover: {obs_3['accepted_value_bps']} bps"
    )

    # Attach follow-up and finalize
    chain.attach_observation(farmer, job_id, obs_id_3)
    chain.finalize_followup(job_id)

    job_settled = chain.escrow_mock.get_job(job_id)
    logger.info(
        f"[STEP 8] Finalized Follow-up! Released retainage to worker. Total Worker Payout: {job_settled['paid_to_worker']} tokens. Final State: {job_settled['state']}"
    )

    assert job_settled["state"] == "Settled"
    assert job_settled["paid_to_worker"] == 100_000
    assert job_settled["refunded_to_farmer"] == 0

    logger.info("==================================================")
    logger.info("SIMULATION COMPLETED SUCCESSFULLY - ALL STAGES PASS")
    logger.info("==================================================")


if __name__ == "__main__":
    run_e2e_simulation()
