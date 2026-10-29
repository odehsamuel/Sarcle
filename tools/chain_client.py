"""Chain client abstraction for Proof-of-Weeding.

Provides unified interface for both local mock execution (zero network required)
and live Stellar Testnet RPC calls.
"""

import os
from typing import Dict, Optional, Tuple
from contract_mock import EvidenceRegistryMock, WorkEscrowMock


class ChainClient:
    def __init__(self, mode: str = "mock", rpc_url: Optional[str] = None):
        self.mode = mode
        self.rpc_url = (
            rpc_url
            or os.environ.get(
                "STELLAR_RPC_URL", "https://soroban-testnet.stellar.org"
            )
        )
        self.registry_mock = EvidenceRegistryMock()
        self.escrow_mock = WorkEscrowMock(self.registry_mock)

        # Pre-initialize mock environment
        self.admin = "GB_ADMIN_MOCK_TESTNET"
        self.registry_mock.init(self.admin)
        self.escrow_mock.init(self.admin)

    def request_challenge(
        self, attester_addr: str, job_ref: int, device_id: bytes, kind: int
    ) -> bytes:
        if self.mode == "mock":
            return self.registry_mock.request_challenge(
                attester_addr, job_ref, device_id, kind
            )
        else:
            # Live Stellar RPC invocation stub
            raise NotImplementedError("Live RPC invocation configured via CLI")

    def submit_observation(
        self,
        attester_addr: str,
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
        if self.mode == "mock":
            return self.registry_mock.submit_observation(
                attester=attester_addr,
                job_ref=job_ref,
                kind=kind,
                image_hash=image_hash,
                roi_hash=roi_hash,
                metric_id=metric_id,
                challenge=challenge,
                counter=counter,
                timestamp=timestamp,
                signature=signature,
                analyzer_hash=analyzer_hash,
                value_bps=value_bps,
            )
        else:
            raise NotImplementedError("Live RPC invocation configured via CLI")

    def add_analysis(
        self,
        attester_addr: str,
        obs_id: int,
        analyzer_hash: bytes,
        value_bps: int,
    ):
        if self.mode == "mock":
            return self.registry_mock.add_analysis(
                attester=attester_addr,
                obs_id=obs_id,
                analyzer_hash=analyzer_hash,
                value_bps=value_bps,
            )
        else:
            raise NotImplementedError("Live RPC invocation configured via CLI")

    def get_observation(self, obs_id: int) -> Dict:
        return self.registry_mock.get_observation(obs_id)

    def attach_observation(self, caller: str, job_id: int, obs_id: int):
        self.escrow_mock.attach_observation(caller, job_id, obs_id)

    def finalize_completion(self, job_id: int):
        self.escrow_mock.finalize_completion(job_id)

    def finalize_followup(self, job_id: int):
        self.escrow_mock.finalize_followup(job_id)
