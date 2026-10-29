"""Python reference implementation and test mock of Soroban evidence_registry.

Mirrors all validation rules, storage policies, and quorum agreement logic
defined in contracts/evidence_registry/src/lib.rs.
"""

import struct
from typing import Dict, List, Optional, Tuple
from ed25519_compact import checkvalid

DOMAIN_TAG = b"PoW-OBS-v2"


class RegistryError(Exception):
    pass


class EvidenceRegistryMock:
    def __init__(self):
        self.admin: Optional[str] = None
        self.config: Dict = {
            "timestamp_tolerance_secs": 60,
            "challenge_ttl_secs": 300,
            "max_divergence_bps": 500,
            "quorum": 2,
        }
        self.devices: Dict[bytes, Dict] = {}  # device_id -> {status, registered_at}
        self.attesters: Dict[str, Dict] = {}  # attester_addr -> {active, added_at}
        self.analyzers: Dict[bytes, Dict] = {}  # hash -> {metric_id, family_id, active}
        self.last_counters: Dict[bytes, int] = {}  # device_id -> counter
        self.challenges: Dict[bytes, Dict] = {}  # challenge_bytes -> record
        self.observations: Dict[int, Dict] = {}  # obs_id -> record
        self.next_obs_id: int = 1
        self.events: List[Tuple[str, Tuple]] = []
        self.current_timestamp: int = 1700000000

    def init(self, admin: str, config: Optional[Dict] = None):
        if self.admin is not None:
            raise RegistryError("ALREADY_INITIALIZED")
        self.admin = admin
        if config:
            self.config.update(config)

    def register_device(self, admin: str, device_id: bytes):
        if admin != self.admin:
            raise RegistryError("UNAUTHORIZED")
        if device_id in self.devices:
            raise RegistryError("DEVICE_ALREADY_REGISTERED")
        self.devices[device_id] = {
            "public_key": device_id,
            "status": "Active",
            "registered_at": self.current_timestamp,
        }
        self.events.append(("DeviceRegistered", (device_id,)))

    def revoke_device(self, admin: str, device_id: bytes):
        if admin != self.admin:
            raise RegistryError("UNAUTHORIZED")
        if device_id not in self.devices:
            raise RegistryError("DEVICE_NOT_FOUND")
        self.devices[device_id]["status"] = "Revoked"
        self.events.append(("DeviceRevoked", (device_id,)))

    def add_attester(self, admin: str, attester: str):
        if admin != self.admin:
            raise RegistryError("UNAUTHORIZED")
        self.attesters[attester] = {
            "active": True,
            "added_at": self.current_timestamp,
        }
        self.events.append(("AttesterAdded", (attester,)))

    def remove_attester(self, admin: str, attester: str):
        if admin != self.admin:
            raise RegistryError("UNAUTHORIZED")
        if attester not in self.attesters:
            raise RegistryError("ATTESTER_NOT_FOUND")
        self.attesters[attester]["active"] = False
        self.events.append(("AttesterRemoved", (attester,)))

    def allow_analyzer(
        self, admin: str, analyzer_hash: bytes, metric_id: int, family_id: int
    ):
        if admin != self.admin:
            raise RegistryError("UNAUTHORIZED")
        self.analyzers[analyzer_hash] = {
            "metric_id": metric_id,
            "family_id": family_id,
            "active": True,
        }
        self.events.append(("AnalyzerAllowed", (analyzer_hash, metric_id, family_id)))

    def revoke_analyzer(self, admin: str, analyzer_hash: bytes):
        if admin != self.admin:
            raise RegistryError("UNAUTHORIZED")
        if analyzer_hash not in self.analyzers:
            raise RegistryError("ANALYZER_NOT_ALLOWED")
        self.analyzers[analyzer_hash]["active"] = False
        self.events.append(("AnalyzerRevoked", (analyzer_hash,)))

    def request_challenge(
        self, attester: str, job_ref: int, device_id: bytes, kind: int
    ) -> bytes:
        if not self.attesters.get(attester, {}).get("active"):
            raise RegistryError("ATTESTER_NOT_ACTIVE")
        dev = self.devices.get(device_id)
        if not dev:
            raise RegistryError("DEVICE_NOT_FOUND")
        if dev["status"] != "Active":
            raise RegistryError("DEVICE_REVOKED")
        if kind not in (0, 1, 2):
            raise RegistryError("INVALID_OBSERVATION_KIND")

        import os

        challenge = os.urandom(16)
        now = self.current_timestamp
        self.challenges[challenge] = {
            "device_id": device_id,
            "job_ref": job_ref,
            "kind": kind,
            "issued_at": now,
            "expires_at": now + self.config["challenge_ttl_secs"],
            "used": False,
        }
        self.events.append(
            ("ChallengeIssued", (device_id, job_ref, kind, challenge))
        )
        return challenge

    def build_canonical_message(
        self,
        device_id: bytes,
        job_ref: int,
        kind: int,
        counter: int,
        timestamp: int,
        challenge: bytes,
        image_sha256: bytes,
    ) -> bytes:
        msg = bytearray()
        msg.extend(DOMAIN_TAG)
        msg.extend(device_id)
        msg.extend(struct.pack(">Q", job_ref))
        msg.extend(struct.pack("B", kind))
        msg.extend(struct.pack(">Q", counter))
        msg.extend(struct.pack(">Q", timestamp))
        msg.extend(challenge)
        msg.extend(image_sha256)
        assert len(msg) == 115
        return bytes(msg)

    def submit_observation(
        self,
        attester: str,
        job_ref: int,
        kind: int,
        image_hash: bytes,
        roi_hash: bytes,
        metric_id: int,
        challenge: bytes,
        counter: int,
        timestamp: int,
        signature: bytes,
        analyzer_hash: bytes,
        value_bps: int,
    ) -> int:
        if not self.attesters.get(attester, {}).get("active"):
            raise RegistryError("ATTESTER_NOT_ACTIVE")
        if kind not in (0, 1, 2):
            raise RegistryError("INVALID_OBSERVATION_KIND")
        if not (0 <= value_bps <= 10000):
            raise RegistryError("INVALID_METRIC_VALUE")

        chal = self.challenges.get(challenge)
        if not chal:
            raise RegistryError("CHALLENGE_NOT_FOUND")
        if chal["used"]:
            raise RegistryError("CHALLENGE_ALREADY_USED")
        if self.current_timestamp > chal["expires_at"]:
            raise RegistryError("CHALLENGE_EXPIRED")
        if chal["job_ref"] != job_ref or chal["kind"] != kind:
            raise RegistryError("CHALLENGE_MISMATCH")

        device_id = chal["device_id"]
        dev = self.devices.get(device_id)
        if not dev or dev["status"] != "Active":
            raise RegistryError("DEVICE_REVOKED")

        tol = self.config["timestamp_tolerance_secs"]
        if (
            timestamp + tol < chal["issued_at"]
            or timestamp > chal["expires_at"] + tol
        ):
            raise RegistryError("TIMESTAMP_OUT_OF_RANGE")

        last_counter = self.last_counters.get(device_id, 0)
        if counter <= last_counter:
            raise RegistryError("COUNTER_NOT_INCREASING")

        analyzer = self.analyzers.get(analyzer_hash)
        if not analyzer or not analyzer["active"] or analyzer["metric_id"] != metric_id:
            raise RegistryError("ANALYZER_NOT_ALLOWED")

        msg = self.build_canonical_message(
            device_id, job_ref, kind, counter, timestamp, challenge, image_hash
        )
        if not checkvalid(signature, msg, device_id):
            raise RegistryError("SIGNATURE_VERIFICATION_FAILED")

        # Mark used & update state
        chal["used"] = True
        self.last_counters[device_id] = counter

        obs_id = self.next_obs_id
        self.next_obs_id += 1

        analyses = [
            {
                "attester": attester,
                "analyzer_hash": analyzer_hash,
                "family_id": analyzer["family_id"],
                "value_bps": value_bps,
                "recorded_at": self.current_timestamp,
            }
        ]

        status = (
            "Accepted" if self.config["quorum"] == 1 else "PendingQuorum"
        )
        accepted_value = value_bps if status == "Accepted" else None

        self.observations[obs_id] = {
            "obs_id": obs_id,
            "job_ref": job_ref,
            "kind": kind,
            "device_id": device_id,
            "image_hash": image_hash,
            "roi_hash": roi_hash,
            "metric_id": metric_id,
            "timestamp": timestamp,
            "analyses": analyses,
            "status": status,
            "accepted_value_bps": accepted_value,
        }
        self.events.append(
            ("ObservationSubmitted", (obs_id, job_ref, kind, device_id))
        )
        self.events.append(
            ("AnalysisAdded", (obs_id, attester, analyzer_hash, value_bps))
        )
        return obs_id

    def add_analysis(
        self, attester: str, obs_id: int, analyzer_hash: bytes, value_bps: int
    ):
        if not self.attesters.get(attester, {}).get("active"):
            raise RegistryError("ATTESTER_NOT_ACTIVE")
        if not (0 <= value_bps <= 10000):
            raise RegistryError("INVALID_METRIC_VALUE")

        obs = self.observations.get(obs_id)
        if not obs:
            raise RegistryError("OBSERVATION_NOT_FOUND")
        if obs["status"] != "PendingQuorum":
            raise RegistryError("OBSERVATION_ALREADY_QUORUM")

        analyzer = self.analyzers.get(analyzer_hash)
        if not analyzer or not analyzer["active"] or analyzer["metric_id"] != obs["metric_id"]:
            raise RegistryError("ANALYZER_NOT_ALLOWED")

        for existing in obs["analyses"]:
            if existing["attester"] == attester:
                raise RegistryError("DUPLICATE_ATTESTER_ANALYSIS")
            if existing["family_id"] == analyzer["family_id"]:
                raise RegistryError("DUPLICATE_FAMILY_ANALYSIS")

        obs["analyses"].append(
            {
                "attester": attester,
                "analyzer_hash": analyzer_hash,
                "family_id": analyzer["family_id"],
                "value_bps": value_bps,
                "recorded_at": self.current_timestamp,
            }
        )
        self.events.append(
            ("AnalysisAdded", (obs_id, attester, analyzer_hash, value_bps))
        )

        if len(obs["analyses"]) >= self.config["quorum"]:
            val0 = obs["analyses"][0]["value_bps"]
            val1 = obs["analyses"][1]["value_bps"]
            diff = abs(val0 - val1)
            if diff <= self.config["max_divergence_bps"]:
                mean = (val0 + val1) // 2
                obs["status"] = "Accepted"
                obs["accepted_value_bps"] = mean
                self.events.append(("ObservationAccepted", (obs_id, mean)))
            else:
                obs["status"] = "Divergent"
                obs["accepted_value_bps"] = None
                self.events.append(("ObservationDivergent", (obs_id, diff)))

    def get_observation(self, obs_id: int) -> Dict:
        obs = self.observations.get(obs_id)
        if not obs:
            raise RegistryError("OBSERVATION_NOT_FOUND")
        return obs


class EscrowError(Exception):
    pass


class WorkEscrowMock:
    def __init__(self, registry: EvidenceRegistryMock):
        self.registry = registry
        self.admin: Optional[str] = None
        self.next_job_id: int = 1
        self.jobs: Dict[int, Dict] = {}
        self.events: List[Tuple[str, Tuple]] = []

    def init(self, admin: str):
        self.admin = admin

    def create_job(self, params: Dict) -> int:
        if params["amount"] <= 0:
            raise EscrowError("INVALID_AMOUNT")
        if (
            params["threshold_bps"] > 10000
            or params["retainage_bps"] > 10000
            or params["min_baseline_bps"] > 10000
        ):
            raise EscrowError("INVALID_BASIS_POINTS")

        now = self.registry.current_timestamp
        if not (
            now
            < params["baseline_deadline"]
            < params["completion_deadline"]
            < params["followup_deadline"]
        ):
            raise EscrowError("INVALID_DEADLINES")

        job_id = self.next_job_id
        self.next_job_id += 1

        self.jobs[job_id] = {
            "job_id": job_id,
            "farmer": params["farmer"],
            "worker": params["worker"],
            "token": params["token"],
            "amount": params["amount"],
            "device_id": params["device_id"],
            "roi_hash": params["roi_hash"],
            "metric_id": params["metric_id"],
            "arbiter": params["arbiter"],
            "threshold_bps": params["threshold_bps"],
            "min_baseline_bps": params["min_baseline_bps"],
            "retainage_bps": params["retainage_bps"],
            "followup_delay_secs": params["followup_delay_secs"],
            "max_regrowth_bps": params["max_regrowth_bps"],
            "baseline_deadline": params["baseline_deadline"],
            "completion_deadline": params["completion_deadline"],
            "followup_deadline": params["followup_deadline"],
            "challenge_window_secs": params["challenge_window_secs"],
            "state": "Funded",
            "baseline_obs_id": None,
            "completion_obs_id": None,
            "followup_obs_id": None,
            "baseline_cover_bps": None,
            "completion_cover_bps": None,
            "followup_cover_bps": None,
            "baseline_image_hash": None,
            "completion_image_hash": None,
            "completion_recorded_at": None,
            "retained_amount": 0,
            "paid_to_worker": 0,
            "refunded_to_farmer": 0,
            "dispute_timestamp": None,
            "dispute_outcome": None,
        }
        self.events.append(
            ("JobCreated", (job_id, params["farmer"], params["worker"], params["amount"]))
        )
        return job_id

    def attach_observation(self, caller: str, job_id: int, obs_id: int):
        job = self.jobs.get(job_id)
        if not job:
            raise EscrowError("JOB_NOT_FOUND")

        obs = self.registry.get_observation(obs_id)

        if obs["status"] == "Divergent":
            job["state"] = "Disputed"
            job["dispute_timestamp"] = self.registry.current_timestamp
            self.events.append(("JobDisputed", (job_id, caller)))
            return

        if obs["status"] != "Accepted":
            raise EscrowError("OBSERVATION_NOT_ACCEPTED")
        if obs["job_ref"] != job_id:
            raise EscrowError("OBSERVATION_JOB_MISMATCH")
        if obs["device_id"] != job["device_id"]:
            raise EscrowError("OBSERVATION_DEVICE_MISMATCH")
        if obs["roi_hash"] != job["roi_hash"]:
            raise EscrowError("OBSERVATION_ROI_MISMATCH")
        if obs["metric_id"] != job["metric_id"]:
            raise EscrowError("OBSERVATION_METRIC_MISMATCH")

        now = self.registry.current_timestamp
        cover_bps = obs["accepted_value_bps"]

        if obs["kind"] == 0:  # Baseline
            if job["state"] != "Funded":
                raise EscrowError("INVALID_JOB_STATE")
            if now > job["baseline_deadline"]:
                raise EscrowError("DEADLINE_EXCEEDED")
            if cover_bps < job["min_baseline_bps"]:
                raise EscrowError("BASELINE_TOO_LOW")

            job["state"] = "BaselineRecorded"
            job["baseline_obs_id"] = obs_id
            job["baseline_cover_bps"] = cover_bps
            job["baseline_image_hash"] = obs["image_hash"]

        elif obs["kind"] == 1:  # Completion
            if job["state"] != "BaselineRecorded":
                raise EscrowError("INVALID_JOB_STATE")
            if now > job["completion_deadline"]:
                raise EscrowError("DEADLINE_EXCEEDED")
            if obs["image_hash"] == job["baseline_image_hash"]:
                raise EscrowError("DUPLICATE_IMAGE")

            job["state"] = "CompletionRecorded"
            job["completion_obs_id"] = obs_id
            job["completion_cover_bps"] = cover_bps
            job["completion_image_hash"] = obs["image_hash"]
            job["completion_recorded_at"] = now

        elif obs["kind"] == 2:  # Followup
            if job["state"] != "CompletionPaid":
                raise EscrowError("INVALID_JOB_STATE")
            if now > job["followup_deadline"]:
                raise EscrowError("DEADLINE_EXCEEDED")
            comp_time = job["completion_recorded_at"] or 0
            if now < comp_time + job["followup_delay_secs"]:
                raise EscrowError("FOLLOWUP_DELAY_NOT_MET")
            if (
                obs["image_hash"] == job["completion_image_hash"]
                or obs["image_hash"] == job["baseline_image_hash"]
            ):
                raise EscrowError("DUPLICATE_IMAGE")

            job["state"] = "FollowupRecorded"
            job["followup_obs_id"] = obs_id
            job["followup_cover_bps"] = cover_bps
        else:
            raise EscrowError("OBSERVATION_KIND_MISMATCH")

        self.events.append(
            ("ObservationAttached", (job_id, obs_id, obs["kind"], cover_bps))
        )

    def finalize_completion(self, job_id: int):
        job = self.jobs.get(job_id)
        if not job or job["state"] != "CompletionRecorded":
            raise EscrowError("INVALID_JOB_STATE")

        now = self.registry.current_timestamp
        recorded_at = job["completion_recorded_at"]
        if now < recorded_at + job["challenge_window_secs"]:
            raise EscrowError("CHALLENGE_WINDOW_ACTIVE")

        base_cover = job["baseline_cover_bps"]
        comp_cover = job["completion_cover_bps"]
        thresh = job["threshold_bps"]

        # comp_cover * 10000 <= base_cover * (10000 - thresh)
        target_max = base_cover * (10000 - thresh)
        actual_scaled = comp_cover * 10000

        if actual_scaled <= target_max:
            retainage = (job["amount"] * job["retainage_bps"]) // 10000
            payout = job["amount"] - retainage
            job["retained_amount"] = retainage
            job["paid_to_worker"] = payout

            if retainage > 0:
                job["state"] = "CompletionPaid"
            else:
                job["state"] = "Settled"
            self.events.append(
                ("CompletionFinalized", (job_id, payout, 0))
            )
        else:
            job["refunded_to_farmer"] = job["amount"]
            job["state"] = "Refunded"
            self.events.append(
                ("CompletionFinalized", (job_id, 0, job["amount"]))
            )

    def finalize_followup(self, job_id: int):
        job = self.jobs.get(job_id)
        if not job or job["state"] != "FollowupRecorded":
            raise EscrowError("INVALID_JOB_STATE")

        comp_cover = job["completion_cover_bps"]
        fol_cover = job["followup_cover_bps"]
        retainage = job["retained_amount"]

        if fol_cover <= comp_cover + job["max_regrowth_bps"]:
            job["paid_to_worker"] += retainage
            job["state"] = "Settled"
            self.events.append(
                ("FollowupFinalized", (job_id, retainage, 0))
            )
        else:
            job["refunded_to_farmer"] += retainage
            job["state"] = "Settled"
            self.events.append(
                ("FollowupFinalized", (job_id, 0, retainage))
            )

    def dispute(self, caller: str, job_id: int):
        job = self.jobs.get(job_id)
        if not job:
            raise EscrowError("JOB_NOT_FOUND")
        if caller != job["farmer"] and caller != job["worker"]:
            raise EscrowError("UNAUTHORIZED")
        if job["state"] in ("Disputed", "Resolved", "Settled", "Refunded"):
            raise EscrowError("INVALID_JOB_STATE")

        job["state"] = "Disputed"
        job["dispute_timestamp"] = self.registry.current_timestamp
        self.events.append(("JobDisputed", (job_id, caller)))

    def resolve(self, arbiter: str, job_id: int, outcome: str):
        job = self.jobs.get(job_id)
        if not job or job["state"] != "Disputed":
            raise EscrowError("NO_DISPUTE_ACTIVE")
        if arbiter != job["arbiter"]:
            raise EscrowError("UNAUTHORIZED")

        remaining = job["amount"] - job["paid_to_worker"] - job["refunded_to_farmer"]
        if outcome == "FarmerWins":
            job["refunded_to_farmer"] += remaining
        elif outcome == "WorkerWins":
            job["paid_to_worker"] += remaining
        elif outcome == "Split":
            half_worker = remaining // 2
            half_farmer = remaining - half_worker
            job["paid_to_worker"] += half_worker
            job["refunded_to_farmer"] += half_farmer
        else:
            raise EscrowError("INVALID_OUTCOME")

        job["state"] = "Resolved"
        job["dispute_outcome"] = outcome
        self.events.append(("DisputeResolved", (job_id, outcome)))

    def cancel(self, farmer: str, job_id: int):
        job = self.jobs.get(job_id)
        if not job or job["state"] != "Funded":
            raise EscrowError("INVALID_JOB_STATE")
        if farmer != job["farmer"]:
            raise EscrowError("UNAUTHORIZED")

        job["refunded_to_farmer"] = job["amount"]
        job["state"] = "Refunded"
        self.events.append(("JobCancelled", (job_id,)))

    def get_job(self, job_id: int) -> Dict:
        job = self.jobs.get(job_id)
        if not job:
            raise EscrowError("JOB_NOT_FOUND")
        return job
