#![no_std]

pub mod error;
pub mod events;
pub mod storage;
pub mod types;

#[cfg(test)]
mod test;

use error::EscrowError;
use evidence_registry::{types::ObservationStatus, EvidenceRegistryClient};
use soroban_sdk::{
    contract, contractimpl, token, Address, Env,
};
use types::{CreateJobParams, DisputeOutcome, Job, JobState};

pub const DEFAULT_ARBITER_TIMEOUT_SECS: u64 = 604_800; // 7 days

/// WorkEscrow Contract
///
/// Trust and Governance Invariant:
/// The contract administrator has ZERO authority to withdraw, seize, or redirect escrowed funds.
/// Funds can only be disbursed according to the cryptographic state machine, the integer release rule,
/// or the pre-designated per-job arbiter in the event of an explicit dispute.
#[contract]
pub struct WorkEscrow;

#[contractimpl]
impl WorkEscrow {
    /// Initialize the escrow contract with administrative parameters and evidence registry address.
    pub fn init(env: Env, admin: Address, registry_address: Address) -> Result<(), EscrowError> {
        if storage::get_admin(&env).is_some() {
            return Err(EscrowError::AlreadyInitialized);
        }
        storage::set_admin(&env, &admin);
        storage::set_registry_address(&env, &registry_address);
        Ok(())
    }

    /// Create and fund a vegetation clearing job.
    /// Locks the payment tokens into escrow.
    pub fn create_job(env: Env, params: CreateJobParams) -> Result<u64, EscrowError> {
        params.farmer.require_auth();

        if params.amount <= 0 {
            return Err(EscrowError::InvalidAmount);
        }
        if params.threshold_bps > 10000 || params.retainage_bps > 10000 || params.min_baseline_bps > 10000 {
            return Err(EscrowError::InvalidBasisPoints);
        }

        let now = env.ledger().timestamp();
        if now >= params.baseline_deadline
            || params.baseline_deadline >= params.completion_deadline
            || params.completion_deadline >= params.followup_deadline
        {
            return Err(EscrowError::InvalidDeadlines);
        }

        // Lock funds from farmer to contract
        let token_client = token::Client::new(&env, &params.token);
        token_client.transfer(
            &params.farmer,
            &env.current_contract_address(),
            &params.amount,
        );

        let job_id = storage::increment_job_id(&env);
        let job = Job {
            job_id,
            farmer: params.farmer.clone(),
            worker: params.worker.clone(),
            token: params.token.clone(),
            amount: params.amount,
            device_id: params.device_id.clone(),
            roi_hash: params.roi_hash.clone(),
            metric_id: params.metric_id,
            arbiter: params.arbiter.clone(),
            threshold_bps: params.threshold_bps,
            min_baseline_bps: params.min_baseline_bps,
            retainage_bps: params.retainage_bps,
            followup_delay_secs: params.followup_delay_secs,
            max_regrowth_bps: params.max_regrowth_bps,
            baseline_deadline: params.baseline_deadline,
            completion_deadline: params.completion_deadline,
            followup_deadline: params.followup_deadline,
            challenge_window_secs: params.challenge_window_secs,
            state: JobState::Funded,
            baseline_obs_id: None,
            completion_obs_id: None,
            followup_obs_id: None,
            baseline_cover_bps: None,
            completion_cover_bps: None,
            followup_cover_bps: None,
            baseline_image_hash: None,
            completion_image_hash: None,
            completion_recorded_at: None,
            retained_amount: 0,
            paid_to_worker: 0,
            refunded_to_farmer: 0,
            dispute_timestamp: None,
            dispute_outcome: None,
        };

        storage::set_job(&env, job_id, &job);
        events::emit_job_created(&env, job_id, &params.farmer, &params.worker, params.amount);

        Ok(job_id)
    }

    /// Attach an observation from evidence_registry to progress the job state.
    /// Callable permissionlessly by anyone once the observation is registered.
    pub fn attach_observation(
        env: Env,
        caller: Address,
        job_id: u64,
        obs_id: u64,
    ) -> Result<(), EscrowError> {
        caller.require_auth();

        let mut job = storage::get_job(&env, job_id).ok_or(EscrowError::JobNotFound)?;
        let reg_addr = storage::get_registry_address(&env).ok_or(EscrowError::NotInitialized)?;
        let reg_client = EvidenceRegistryClient::new(&env, &reg_addr);

        let obs = reg_client.get_observation(&obs_id);

        // If observation was marked Divergent by quorum failure, immediately flag job as Disputed
        if obs.status == ObservationStatus::Divergent {
            job.state = JobState::Disputed;
            job.dispute_timestamp = Some(env.ledger().timestamp());
            storage::set_job(&env, job_id, &job);
            events::emit_job_disputed(&env, job_id, &caller);
            return Ok(());
        }

        if obs.status != ObservationStatus::Accepted {
            return Err(EscrowError::ObservationNotAccepted);
        }
        if obs.job_ref != job_id {
            return Err(EscrowError::ObservationJobMismatch);
        }
        if obs.device_id != job.device_id {
            return Err(EscrowError::ObservationDeviceMismatch);
        }
        if obs.roi_hash != job.roi_hash {
            return Err(EscrowError::ObservationRoiMismatch);
        }
        if obs.metric_id != job.metric_id {
            return Err(EscrowError::ObservationMetricMismatch);
        }

        let now = env.ledger().timestamp();
        let cover_bps = obs.accepted_value_bps.ok_or(EscrowError::ObservationNotAccepted)?;

        match obs.kind {
            // Kind 0: Baseline
            0 => {
                if job.state != JobState::Funded {
                    return Err(EscrowError::InvalidJobState);
                }
                if now > job.baseline_deadline {
                    return Err(EscrowError::DeadlineExceeded);
                }
                if cover_bps < job.min_baseline_bps {
                    return Err(EscrowError::BaselineTooLow);
                }

                job.state = JobState::BaselineRecorded;
                job.baseline_obs_id = Some(obs_id);
                job.baseline_cover_bps = Some(cover_bps);
                job.baseline_image_hash = Some(obs.image_hash.clone());
            }

            // Kind 1: Completion
            1 => {
                if job.state != JobState::BaselineRecorded {
                    return Err(EscrowError::InvalidJobState);
                }
                if now > job.completion_deadline {
                    return Err(EscrowError::DeadlineExceeded);
                }
                if let Some(ref base_img) = job.baseline_image_hash {
                    if *base_img == obs.image_hash {
                        return Err(EscrowError::DuplicateImage);
                    }
                }

                job.state = JobState::CompletionRecorded;
                job.completion_obs_id = Some(obs_id);
                job.completion_cover_bps = Some(cover_bps);
                job.completion_image_hash = Some(obs.image_hash.clone());
                job.completion_recorded_at = Some(now);
            }

            // Kind 2: Followup (Retainage stage)
            2 => {
                if job.state != JobState::CompletionPaid {
                    return Err(EscrowError::InvalidJobState);
                }
                if now > job.followup_deadline {
                    return Err(EscrowError::DeadlineExceeded);
                }
                let comp_time = job.completion_recorded_at.unwrap_or(0);
                if now < comp_time + job.followup_delay_secs {
                    return Err(EscrowError::FollowupDelayNotMet);
                }
                if let Some(ref comp_img) = job.completion_image_hash {
                    if *comp_img == obs.image_hash {
                        return Err(EscrowError::DuplicateImage);
                    }
                }
                if let Some(ref base_img) = job.baseline_image_hash {
                    if *base_img == obs.image_hash {
                        return Err(EscrowError::DuplicateImage);
                    }
                }

                job.state = JobState::FollowupRecorded;
                job.followup_obs_id = Some(obs_id);
                job.followup_cover_bps = Some(cover_bps);
            }

            _ => return Err(EscrowError::ObservationKindMismatch),
        }

        storage::set_job(&env, job_id, &job);
        events::emit_observation_attached(&env, job_id, obs_id, obs.kind, cover_bps);

        Ok(())
    }

    /// Finalize completion after the challenge window has elapsed without dispute.
    /// Evaluates the integer vegetation reduction formula:
    /// completion_cover * 10,000 <= baseline_cover * (10,000 - threshold_bps)
    pub fn finalize_completion(env: Env, job_id: u64) -> Result<(), EscrowError> {
        let mut job = storage::get_job(&env, job_id).ok_or(EscrowError::JobNotFound)?;
        if job.state != JobState::CompletionRecorded {
            return Err(EscrowError::InvalidJobState);
        }

        let now = env.ledger().timestamp();
        let recorded_at = job.completion_recorded_at.ok_or(EscrowError::InvalidJobState)?;
        if now < recorded_at + job.challenge_window_secs {
            return Err(EscrowError::ChallengeWindowActive);
        }

        let base_cover = job.baseline_cover_bps.ok_or(EscrowError::InvalidJobState)? as u128;
        let comp_cover = job.completion_cover_bps.ok_or(EscrowError::InvalidJobState)? as u128;
        let thresh = job.threshold_bps as u128;

        // Formula widened to u128:
        // comp_cover * 10000 <= base_cover * (10000 - thresh)
        let target_max = base_cover
            .checked_mul(10000 - thresh)
            .ok_or(EscrowError::MathOverflow)?;
        let actual_scaled = comp_cover
            .checked_mul(10000)
            .ok_or(EscrowError::MathOverflow)?;

        let token_client = token::Client::new(&env, &job.token);
        let contract_addr = env.current_contract_address();

        if actual_scaled <= target_max {
            // Success: Compute primary payout vs retainage
            let retainage = (job.amount * (job.retainage_bps as i128)) / 10000;
            let payout = job.amount - retainage;

            job.retained_amount = retainage;
            job.paid_to_worker = payout;

            if payout > 0 {
                token_client.transfer(&contract_addr, &job.worker, &payout);
            }

            if retainage > 0 {
                job.state = JobState::CompletionPaid;
            } else {
                job.state = JobState::Settled;
            }

            events::emit_completion_finalized(&env, job_id, payout, 0);
        } else {
            // Failure: Target reduction not achieved, full refund to farmer
            job.refunded_to_farmer = job.amount;
            job.state = JobState::Refunded;

            token_client.transfer(&contract_addr, &job.farmer, &job.amount);
            events::emit_completion_finalized(&env, job_id, 0, job.amount);
        }

        storage::set_job(&env, job_id, &job);
        Ok(())
    }

    /// Finalize follow-up observation to release or refund the retainage.
    /// Evaluates regrowth: followup_cover <= completion_cover + max_regrowth_bps
    pub fn finalize_followup(env: Env, job_id: u64) -> Result<(), EscrowError> {
        let mut job = storage::get_job(&env, job_id).ok_or(EscrowError::JobNotFound)?;
        if job.state != JobState::FollowupRecorded {
            return Err(EscrowError::InvalidJobState);
        }

        let comp_cover = job.completion_cover_bps.ok_or(EscrowError::InvalidJobState)?;
        let fol_cover = job.followup_cover_bps.ok_or(EscrowError::InvalidJobState)?;

        let token_client = token::Client::new(&env, &job.token);
        let contract_addr = env.current_contract_address();
        let retainage = job.retained_amount;

        if fol_cover <= comp_cover + job.max_regrowth_bps {
            // Weeds did not regrow past tolerance: Release retainage to worker
            job.paid_to_worker += retainage;
            job.state = JobState::Settled;

            if retainage > 0 {
                token_client.transfer(&contract_addr, &job.worker, &retainage);
            }
            events::emit_followup_finalized(&env, job_id, retainage, 0);
        } else {
            // Regrowth exceeded tolerance: Refund retainage to farmer
            job.refunded_to_farmer += retainage;
            job.state = JobState::Settled;

            if retainage > 0 {
                token_client.transfer(&contract_addr, &job.farmer, &retainage);
            }
            events::emit_followup_finalized(&env, job_id, 0, retainage);
        }

        storage::set_job(&env, job_id, &job);
        Ok(())
    }

    /// File a dispute (farmer or worker only).
    pub fn dispute(env: Env, caller: Address, job_id: u64) -> Result<(), EscrowError> {
        caller.require_auth();

        let mut job = storage::get_job(&env, job_id).ok_or(EscrowError::JobNotFound)?;
        if caller != job.farmer && caller != job.worker {
            return Err(EscrowError::Unauthorized);
        }
        if job.state == JobState::Disputed || job.state == JobState::Resolved || job.state == JobState::Settled || job.state == JobState::Refunded {
            return Err(EscrowError::InvalidJobState);
        }

        job.state = JobState::Disputed;
        job.dispute_timestamp = Some(env.ledger().timestamp());
        storage::set_job(&env, job_id, &job);

        events::emit_job_disputed(&env, job_id, &caller);
        Ok(())
    }

    /// Arbiter resolves an active dispute.
    pub fn resolve(
        env: Env,
        arbiter: Address,
        job_id: u64,
        outcome: DisputeOutcome,
    ) -> Result<(), EscrowError> {
        arbiter.require_auth();

        let mut job = storage::get_job(&env, job_id).ok_or(EscrowError::JobNotFound)?;
        if arbiter != job.arbiter {
            return Err(EscrowError::Unauthorized);
        }
        if job.state != JobState::Disputed {
            return Err(EscrowError::NoDisputeActive);
        }

        let remaining = job.amount - job.paid_to_worker - job.refunded_to_farmer;
        let token_client = token::Client::new(&env, &job.token);
        let contract_addr = env.current_contract_address();

        match outcome {
            DisputeOutcome::FarmerWins => {
                job.refunded_to_farmer += remaining;
                if remaining > 0 {
                    token_client.transfer(&contract_addr, &job.farmer, &remaining);
                }
            }
            DisputeOutcome::WorkerWins => {
                job.paid_to_worker += remaining;
                if remaining > 0 {
                    token_client.transfer(&contract_addr, &job.worker, &remaining);
                }
            }
            DisputeOutcome::Split => {
                let half_worker = remaining / 2;
                let half_farmer = remaining - half_worker;

                job.paid_to_worker += half_worker;
                job.refunded_to_farmer += half_farmer;

                if half_worker > 0 {
                    token_client.transfer(&contract_addr, &job.worker, &half_worker);
                }
                if half_farmer > 0 {
                    token_client.transfer(&contract_addr, &job.farmer, &half_farmer);
                }
            }
        }

        job.state = JobState::Resolved;
        job.dispute_outcome = Some(outcome);
        storage::set_job(&env, job_id, &job);

        events::emit_dispute_resolved(&env, job_id, outcome);
        Ok(())
    }

    /// Farmer cancels job before baseline observation is recorded.
    pub fn cancel(env: Env, farmer: Address, job_id: u64) -> Result<(), EscrowError> {
        farmer.require_auth();

        let mut job = storage::get_job(&env, job_id).ok_or(EscrowError::JobNotFound)?;
        if farmer != job.farmer {
            return Err(EscrowError::Unauthorized);
        }
        if job.state != JobState::Funded {
            return Err(EscrowError::InvalidJobState);
        }

        let token_client = token::Client::new(&env, &job.token);
        let contract_addr = env.current_contract_address();

        job.refunded_to_farmer = job.amount;
        job.state = JobState::Refunded;
        token_client.transfer(&contract_addr, &job.farmer, &job.amount);

        storage::set_job(&env, job_id, &job);
        events::emit_job_cancelled(&env, job_id);
        Ok(())
    }

    /// Reclaim expired job if deadlines pass without required observations.
    pub fn reclaim_expired(env: Env, farmer: Address, job_id: u64) -> Result<(), EscrowError> {
        farmer.require_auth();

        let mut job = storage::get_job(&env, job_id).ok_or(EscrowError::JobNotFound)?;
        if farmer != job.farmer {
            return Err(EscrowError::Unauthorized);
        }

        let now = env.ledger().timestamp();
        let can_reclaim = match job.state {
            JobState::Funded => now > job.baseline_deadline,
            JobState::BaselineRecorded => now > job.completion_deadline,
            _ => false,
        };

        if !can_reclaim {
            return Err(EscrowError::InvalidJobState);
        }

        let remaining = job.amount - job.paid_to_worker - job.refunded_to_farmer;
        let token_client = token::Client::new(&env, &job.token);
        let contract_addr = env.current_contract_address();

        job.refunded_to_farmer += remaining;
        job.state = JobState::Refunded;
        if remaining > 0 {
            token_client.transfer(&contract_addr, &job.farmer, &remaining);
        }

        storage::set_job(&env, job_id, &job);
        events::emit_job_expired_reclaimed(&env, job_id);
        Ok(())
    }

    /// Arbiter timeout recovery (Section 13 decision):
    /// If an active dispute is not resolved within DEFAULT_ARBITER_TIMEOUT_SECS, farmer may reclaim remaining funds.
    pub fn reclaim_disputed_timeout(
        env: Env,
        farmer: Address,
        job_id: u64,
    ) -> Result<(), EscrowError> {
        farmer.require_auth();

        let mut job = storage::get_job(&env, job_id).ok_or(EscrowError::JobNotFound)?;
        if farmer != job.farmer {
            return Err(EscrowError::Unauthorized);
        }
        if job.state != JobState::Disputed {
            return Err(EscrowError::NoDisputeActive);
        }

        let now = env.ledger().timestamp();
        let disp_time = job.dispute_timestamp.ok_or(EscrowError::NoDisputeActive)?;
        if now < disp_time + DEFAULT_ARBITER_TIMEOUT_SECS {
            return Err(EscrowError::ArbiterTimeoutNotReached);
        }

        let remaining = job.amount - job.paid_to_worker - job.refunded_to_farmer;
        let token_client = token::Client::new(&env, &job.token);
        let contract_addr = env.current_contract_address();

        job.refunded_to_farmer += remaining;
        job.state = JobState::Refunded;
        if remaining > 0 {
            token_client.transfer(&contract_addr, &job.farmer, &remaining);
        }

        storage::set_job(&env, job_id, &job);
        events::emit_dispute_resolved(&env, job_id, DisputeOutcome::FarmerWins);
        Ok(())
    }

    // --- Views ---

    pub fn get_job(env: Env, job_id: u64) -> Result<Job, EscrowError> {
        storage::get_job(&env, job_id).ok_or(EscrowError::JobNotFound)
    }
}
