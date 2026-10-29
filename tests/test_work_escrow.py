"""Unit tests for work_escrow state machine, integer release rule, and retainage."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from contract_mock import (
    EvidenceRegistryMock,
    WorkEscrowMock,
    EscrowError,
)
from ed25519_compact import publickey


class TestWorkEscrowContract(unittest.TestCase):
    def setUp(self):
        self.registry = EvidenceRegistryMock()
        self.escrow = WorkEscrowMock(self.registry)

        self.admin = "G_ADMIN"
        self.farmer = "G_FARMER"
        self.worker = "G_WORKER"
        self.arbiter = "G_ARBITER"
        self.attester_a = "G_ATTESTER_A"
        self.attester_b = "G_ATTESTER_B"

        self.device_sk = bytes.fromhex(
            "1c8aff950685c2ed4bc3174f3472287b56d9517b9c948127319a09a7a36deac8"
        )
        self.device_pk = publickey(self.device_sk)

        self.registry.init(self.admin)
        self.registry.register_device(self.admin, self.device_pk)
        self.registry.add_attester(self.admin, self.attester_a)
        self.registry.add_attester(self.admin, self.attester_b)

        self.escrow.init(self.admin)

        self.roi_hash = b"\x08" * 32
        self.default_params = {
            "farmer": self.farmer,
            "worker": self.worker,
            "token": "CDUMMYTOKEN",
            "amount": 1_000_000,
            "device_id": self.device_pk,
            "roi_hash": self.roi_hash,
            "metric_id": 1,
            "arbiter": self.arbiter,
            "threshold_bps": 7500,  # 75% reduction
            "min_baseline_bps": 4000,  # 40% initial green cover
            "retainage_bps": 2000,  # 20% retainage
            "followup_delay_secs": 86400,
            "max_regrowth_bps": 500,  # 5% max regrowth
            "baseline_deadline": 1700010000,
            "completion_deadline": 1700020000,
            "followup_deadline": 1700200000,
            "challenge_window_secs": 3600,
        }

    def test_full_happy_path_with_retainage(self):
        job_id = self.escrow.create_job(self.default_params)
        self.assertEqual(self.escrow.get_job(job_id)["state"], "Funded")

        # 1. Attach Baseline (6000 bps)
        self.registry.observations[101] = {
            "obs_id": 101,
            "job_ref": job_id,
            "kind": 0,
            "device_id": self.device_pk,
            "image_hash": b"\x01" * 32,
            "roi_hash": self.roi_hash,
            "metric_id": 1,
            "timestamp": 1700001000,
            "status": "Accepted",
            "accepted_value_bps": 6000,
        }
        self.escrow.attach_observation(self.farmer, job_id, 101)
        self.assertEqual(
            self.escrow.get_job(job_id)["state"], "BaselineRecorded"
        )

        # 2. Attach Completion (1200 bps)
        # Required threshold: 6000 * (10000 - 7500) / 10000 = 1500 bps max.
        # 1200 <= 1500 -> PASS!
        self.registry.observations[102] = {
            "obs_id": 102,
            "job_ref": job_id,
            "kind": 1,
            "device_id": self.device_pk,
            "image_hash": b"\x02" * 32,
            "roi_hash": self.roi_hash,
            "metric_id": 1,
            "timestamp": 1700015000,
            "status": "Accepted",
            "accepted_value_bps": 1200,
        }
        self.escrow.attach_observation(self.worker, job_id, 102)
        self.assertEqual(
            self.escrow.get_job(job_id)["state"], "CompletionRecorded"
        )

        # Premature finalize during challenge window fails
        with self.assertRaises(EscrowError):
            self.escrow.finalize_completion(job_id)

        # Advance past challenge window
        self.registry.current_timestamp = 1700015000 + 3601
        self.escrow.finalize_completion(job_id)

        job = self.escrow.get_job(job_id)
        self.assertEqual(job["state"], "CompletionPaid")
        self.assertEqual(job["paid_to_worker"], 800_000)
        self.assertEqual(job["retained_amount"], 200_000)

        # 3. Attach Follow-up (1500 bps)
        # Regrowth = 1500 - 1200 = 300 bps <= 500 bps max_regrowth -> PASS!
        self.registry.current_timestamp = 1700015000 + 86400 + 100
        self.registry.observations[103] = {
            "obs_id": 103,
            "job_ref": job_id,
            "kind": 2,
            "device_id": self.device_pk,
            "image_hash": b"\x03" * 32,
            "roi_hash": self.roi_hash,
            "metric_id": 1,
            "timestamp": self.registry.current_timestamp,
            "status": "Accepted",
            "accepted_value_bps": 1500,
        }
        self.escrow.attach_observation(self.farmer, job_id, 103)
        self.assertEqual(
            self.escrow.get_job(job_id)["state"], "FollowupRecorded"
        )

        self.escrow.finalize_followup(job_id)
        job_settled = self.escrow.get_job(job_id)
        self.assertEqual(job_settled["state"], "Settled")
        self.assertEqual(job_settled["paid_to_worker"], 1_000_000)
        self.assertEqual(job_settled["refunded_to_farmer"], 0)

    def test_threshold_boundary_cases(self):
        # Target: baseline 5000 bps, threshold 5000 (50% reduction).
        # Target max completion = 5000 * 5000 / 10000 = 2500 bps.
        params = dict(self.default_params)
        params["threshold_bps"] = 5000
        params["retainage_bps"] = 0
        params["challenge_window_secs"] = 0

        # Exact boundary: 2500 bps -> Worker wins payout
        job1 = self.escrow.create_job(params)
        self.registry.observations[201] = {
            "obs_id": 201,
            "job_ref": job1,
            "kind": 0,
            "device_id": self.device_pk,
            "image_hash": b"\x21" * 32,
            "roi_hash": self.roi_hash,
            "metric_id": 1,
            "timestamp": 1700001000,
            "status": "Accepted",
            "accepted_value_bps": 5000,
        }
        self.registry.observations[202] = {
            "obs_id": 202,
            "job_ref": job1,
            "kind": 1,
            "device_id": self.device_pk,
            "image_hash": b"\x22" * 32,
            "roi_hash": self.roi_hash,
            "metric_id": 1,
            "timestamp": 1700002000,
            "status": "Accepted",
            "accepted_value_bps": 2500,
        }
        self.escrow.attach_observation(self.farmer, job1, 201)
        self.escrow.attach_observation(self.farmer, job1, 202)
        self.escrow.finalize_completion(job1)
        self.assertEqual(self.escrow.get_job(job1)["state"], "Settled")
        self.assertEqual(self.escrow.get_job(job1)["paid_to_worker"], 1_000_000)

        # One point over: 2501 bps -> Farmer gets full refund
        job2 = self.escrow.create_job(params)
        self.registry.observations[301] = {
            "obs_id": 301,
            "job_ref": job2,
            "kind": 0,
            "device_id": self.device_pk,
            "image_hash": b"\x31" * 32,
            "roi_hash": self.roi_hash,
            "metric_id": 1,
            "timestamp": 1700001000,
            "status": "Accepted",
            "accepted_value_bps": 5000,
        }
        self.registry.observations[302] = {
            "obs_id": 302,
            "job_ref": job2,
            "kind": 1,
            "device_id": self.device_pk,
            "image_hash": b"\x32" * 32,
            "roi_hash": self.roi_hash,
            "metric_id": 1,
            "timestamp": 1700002000,
            "status": "Accepted",
            "accepted_value_bps": 2501,
        }
        self.escrow.attach_observation(self.farmer, job2, 301)
        self.escrow.attach_observation(self.farmer, job2, 302)
        self.escrow.finalize_completion(job2)
        self.assertEqual(self.escrow.get_job(job2)["state"], "Refunded")
        self.assertEqual(
            self.escrow.get_job(job2)["refunded_to_farmer"], 1_000_000
        )

    def test_divergent_observation_triggers_dispute(self):
        job_id = self.escrow.create_job(self.default_params)
        self.registry.observations[401] = {
            "obs_id": 401,
            "job_ref": job_id,
            "kind": 0,
            "device_id": self.device_pk,
            "image_hash": b"\x41" * 32,
            "roi_hash": self.roi_hash,
            "metric_id": 1,
            "timestamp": 1700001000,
            "status": "Divergent",
            "accepted_value_bps": None,
        }
        self.escrow.attach_observation(self.worker, job_id, 401)
        self.assertEqual(self.escrow.get_job(job_id)["state"], "Disputed")

    def test_balance_invariants(self):
        job_id = self.escrow.create_job(self.default_params)
        job = self.escrow.get_job(job_id)
        # Invariant 1: Total disbursed <= initial amount
        total_out = job["paid_to_worker"] + job["refunded_to_farmer"]
        self.assertLessEqual(total_out, job["amount"])


if __name__ == "__main__":
    unittest.main()
