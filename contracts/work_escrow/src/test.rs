#![cfg(test)]

use crate::{
    error::EscrowError,
    types::{CreateJobParams, DisputeOutcome, JobState},
    WorkEscrow, WorkEscrowClient,
};
use evidence_registry::{
    types::{Observation, ObservationStatus, RegistryConfig},
    EvidenceRegistry, EvidenceRegistryClient,
};
use soroban_sdk::{
    testutils::{Address as _, BytesN as _, Ledger},
    token::{StellarAssetClient, TokenClient},
    Address, BytesN, Env, Vec,
};

fn setup_escrow() -> (
    Env,
    WorkEscrowClient<'static>,
    EvidenceRegistryClient<'static>,
    Address,
    Address,
    Address,
    Address,
    Address,
    BytesN<32>,
    BytesN<32>,
) {
    let env = Env::default();
    env.mock_all_auths();
    env.ledger().set_timestamp(1700000000);

    let admin = Address::generate(&env);
    let farmer = Address::generate(&env);
    let worker = Address::generate(&env);
    let arbiter = Address::generate(&env);

    // Register Evidence Registry
    let reg_id = env.register(EvidenceRegistry, ());
    let reg_client = EvidenceRegistryClient::new(&env, &reg_id);
    let reg_config = RegistryConfig {
        timestamp_tolerance_secs: 60,
        challenge_ttl_secs: 300,
        max_divergence_bps: 500,
        quorum: 2,
    };
    reg_client.init(&admin, &reg_config);

    // Register Work Escrow
    let escrow_id = env.register(WorkEscrow, ());
    let escrow_client = WorkEscrowClient::new(&env, &escrow_id);
    escrow_client.init(&admin, &reg_id);

    // Deploy test SEP-41 token
    let token_admin = Address::generate(&env);
    let token_id = env.register_stellar_asset_contract_v2(token_admin.clone());
    let token_admin_client = StellarAssetClient::new(&env, &token_id.address());
    token_admin_client.mint(&farmer, &10_000_000);

    let device_id = BytesN::from_array(&env, &[7u8; 32]);
    reg_client.register_device(&admin, &device_id);

    let roi_hash = BytesN::from_array(&env, &[8u8; 32]);

    (
        env,
        escrow_client,
        reg_client,
        admin,
        farmer,
        worker,
        arbiter,
        token_id.address(),
        device_id,
        roi_hash,
    )
}

#[test]
fn test_create_job_and_cancel() {
    let (env, escrow, _, _, farmer, worker, arbiter, token, device_id, roi_hash) =
        setup_escrow();

    let params = CreateJobParams {
        farmer: farmer.clone(),
        worker: worker.clone(),
        token: token.clone(),
        amount: 1_000_000,
        device_id: device_id.clone(),
        roi_hash: roi_hash.clone(),
        metric_id: 1,
        arbiter: arbiter.clone(),
        threshold_bps: 8000,    // 80% reduction required
        min_baseline_bps: 4000, // at least 40% initial green cover
        retainage_bps: 2000,    // 20% retainage
        followup_delay_secs: 86400,
        max_regrowth_bps: 500,
        baseline_deadline: 1700010000,
        completion_deadline: 1700020000,
        followup_deadline: 1700120000,
        challenge_window_secs: 3600,
    };

    let job_id = escrow.create_job(&params);
    assert_eq!(job_id, 1);

    let job = escrow.get_job(&job_id);
    assert_eq!(job.state, JobState::Funded);

    // Cancel before baseline recorded -> full refund
    escrow.cancel(&farmer, &job_id);
    let job_cancelled = escrow.get_job(&job_id);
    assert_eq!(job_cancelled.state, JobState::Refunded);
    assert_eq!(job_cancelled.refunded_to_farmer, 1_000_000);
}

#[test]
fn test_happy_path_with_retainage_and_followup() {
    let (env, escrow, reg, admin, farmer, worker, arbiter, token, device_id, roi_hash) =
        setup_escrow();

    let params = CreateJobParams {
        farmer: farmer.clone(),
        worker: worker.clone(),
        token: token.clone(),
        amount: 1_000_000,
        device_id: device_id.clone(),
        roi_hash: roi_hash.clone(),
        metric_id: 1,
        arbiter: arbiter.clone(),
        threshold_bps: 8000, // 80% reduction
        min_baseline_bps: 4000,
        retainage_bps: 2000, // 20% retained (200,000 tokens)
        followup_delay_secs: 86400,
        max_regrowth_bps: 500, // 5% max regrowth
        baseline_deadline: 1700010000,
        completion_deadline: 1700020000,
        followup_deadline: 1700200000,
        challenge_window_secs: 3600,
    };

    let job_id = escrow.create_job(&params);

    // Mock Observation 1: Baseline = 6000 bps (60%)
    let base_img = BytesN::from_array(&env, &[11u8; 32]);
    let base_obs = Observation {
        obs_id: 101,
        job_ref: job_id,
        kind: 0,
        device_id: device_id.clone(),
        image_hash: base_img.clone(),
        roi_hash: roi_hash.clone(),
        metric_id: 1,
        timestamp: 1700001000,
        analyses: Vec::new(&env),
        status: ObservationStatus::Accepted,
        accepted_value_bps: Some(6000),
    };
    evidence_registry::storage::set_observation(&env, 101, &base_obs);

    // Attach Baseline
    let caller = Address::generate(&env);
    escrow.attach_observation(&caller, &job_id, &101);
    assert_eq!(escrow.get_job(&job_id).state, JobState::BaselineRecorded);

    // Mock Observation 2: Completion = 1000 bps (10%)
    // Target threshold: 6000 * (10000 - 8000) / 10000 = 1200 bps. 1000 <= 1200 -> PASS!
    let comp_img = BytesN::from_array(&env, &[22u8; 32]);
    let comp_obs = Observation {
        obs_id: 102,
        job_ref: job_id,
        kind: 1,
        device_id: device_id.clone(),
        image_hash: comp_img.clone(),
        roi_hash: roi_hash.clone(),
        metric_id: 1,
        timestamp: 1700015000,
        analyses: Vec::new(&env),
        status: ObservationStatus::Accepted,
        accepted_value_bps: Some(1000),
    };
    evidence_registry::storage::set_observation(&env, 102, &comp_obs);

    // Attach Completion
    escrow.attach_observation(&caller, &job_id, &102);
    assert_eq!(escrow.get_job(&job_id).state, JobState::CompletionRecorded);

    // Premature finalize during challenge window (3600s) -> ChallengeWindowActive
    assert_eq!(
        escrow.try_finalize_completion(&job_id).unwrap_err().unwrap(),
        EscrowError::ChallengeWindowActive
    );

    // Advance ledger past challenge window
    env.ledger().set_timestamp(1700015000 + 3601);
    escrow.finalize_completion(&job_id);

    let job_post_comp = escrow.get_job(&job_id);
    assert_eq!(job_post_comp.state, JobState::CompletionPaid);
    assert_eq!(job_post_comp.paid_to_worker, 800_000); // 80% paid
    assert_eq!(job_post_comp.retained_amount, 200_000); // 20% held

    // Mock Observation 3: Follow-up = 1200 bps (12%)
    // Regrowth: 1200 - 1000 = 200 bps <= 500 bps -> PASS!
    env.ledger().set_timestamp(1700015000 + 86400 + 10);
    let fol_img = BytesN::from_array(&env, &[33u8; 32]);
    let fol_obs = Observation {
        obs_id: 103,
        job_ref: job_id,
        kind: 2,
        device_id: device_id.clone(),
        image_hash: fol_img.clone(),
        roi_hash: roi_hash.clone(),
        metric_id: 1,
        timestamp: env.ledger().timestamp(),
        analyses: Vec::new(&env),
        status: ObservationStatus::Accepted,
        accepted_value_bps: Some(1200),
    };
    evidence_registry::storage::set_observation(&env, 103, &fol_obs);

    escrow.attach_observation(&caller, &job_id, &103);
    assert_eq!(escrow.get_job(&job_id).state, JobState::FollowupRecorded);

    // Finalize follow-up
    escrow.finalize_followup(&job_id);
    let job_final = escrow.get_job(&job_id);
    assert_eq!(job_final.state, JobState::Settled);
    assert_eq!(job_final.paid_to_worker, 1_000_000); // Total 100% paid
    assert_eq!(job_final.refunded_to_farmer, 0);
}

#[test]
fn test_threshold_boundary_failure_and_full_refund() {
    let (env, escrow, _, _, farmer, worker, arbiter, token, device_id, roi_hash) =
        setup_escrow();

    let params = CreateJobParams {
        farmer: farmer.clone(),
        worker: worker.clone(),
        token: token.clone(),
        amount: 1_000_000,
        device_id: device_id.clone(),
        roi_hash: roi_hash.clone(),
        metric_id: 1,
        arbiter: arbiter.clone(),
        threshold_bps: 5000, // 50% reduction required
        min_baseline_bps: 4000,
        retainage_bps: 0, // No retainage
        followup_delay_secs: 86400,
        max_regrowth_bps: 500,
        baseline_deadline: 1700010000,
        completion_deadline: 1700020000,
        followup_deadline: 1700200000,
        challenge_window_secs: 60,
    };

    let job_id = escrow.create_job(&params);
    let caller = Address::generate(&env);

    // Baseline = 5000 bps
    let base_obs = Observation {
        obs_id: 201,
        job_ref: job_id,
        kind: 0,
        device_id: device_id.clone(),
        image_hash: BytesN::from_array(&env, &[1u8; 32]),
        roi_hash: roi_hash.clone(),
        metric_id: 1,
        timestamp: 1700001000,
        analyses: Vec::new(&env),
        status: ObservationStatus::Accepted,
        accepted_value_bps: Some(5000),
    };
    evidence_registry::storage::set_observation(&env, 201, &base_obs);
    escrow.attach_observation(&caller, &job_id, &201);

    // Target threshold: 5000 * (10000 - 5000) / 10000 = 2500 bps.
    // One bps over (2501 bps) -> FAILS threshold!
    let comp_obs = Observation {
        obs_id: 202,
        job_ref: job_id,
        kind: 1,
        device_id: device_id.clone(),
        image_hash: BytesN::from_array(&env, &[2u8; 32]),
        roi_hash: roi_hash.clone(),
        metric_id: 1,
        timestamp: 1700002000,
        analyses: Vec::new(&env),
        status: ObservationStatus::Accepted,
        accepted_value_bps: Some(2501),
    };
    evidence_registry::storage::set_observation(&env, 202, &comp_obs);
    escrow.attach_observation(&caller, &job_id, &202);

    env.ledger().set_timestamp(1700002000 + 61);
    escrow.finalize_completion(&job_id);

    let job = escrow.get_job(&job_id);
    assert_eq!(job.state, JobState::Refunded);
    assert_eq!(job.paid_to_worker, 0);
    assert_eq!(job.refunded_to_farmer, 1_000_000);
}

#[test]
fn test_dispute_and_arbiter_resolution() {
    let (env, escrow, _, _, farmer, worker, arbiter, token, device_id, roi_hash) =
        setup_escrow();

    let params = CreateJobParams {
        farmer: farmer.clone(),
        worker: worker.clone(),
        token: token.clone(),
        amount: 1_000_000,
        device_id: device_id.clone(),
        roi_hash: roi_hash.clone(),
        metric_id: 1,
        arbiter: arbiter.clone(),
        threshold_bps: 5000,
        min_baseline_bps: 4000,
        retainage_bps: 0,
        followup_delay_secs: 86400,
        max_regrowth_bps: 500,
        baseline_deadline: 1700010000,
        completion_deadline: 1700020000,
        followup_deadline: 1700200000,
        challenge_window_secs: 3600,
    };

    let job_id = escrow.create_job(&params);
    let caller = Address::generate(&env);

    // Farmer files dispute
    escrow.dispute(&farmer, &job_id);
    assert_eq!(escrow.get_job(&job_id).state, JobState::Disputed);

    // Arbiter splits funds 50/50
    escrow.resolve(&arbiter, &job_id, DisputeOutcome::Split);
    let job = escrow.get_job(&job_id);
    assert_eq!(job.state, JobState::Resolved);
    assert_eq!(job.paid_to_worker, 500_000);
    assert_eq!(job.refunded_to_farmer, 500_000);
}
