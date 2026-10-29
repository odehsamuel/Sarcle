use soroban_sdk::{symbol_short, Address, Env};

use crate::types::DisputeOutcome;

pub fn emit_job_created(env: &Env, job_id: u64, farmer: &Address, worker: &Address, amount: i128) {
    let topics = (symbol_short!("job_crt"), job_id);
    env.events().publish(topics, (farmer.clone(), worker.clone(), amount));
}

pub fn emit_observation_attached(env: &Env, job_id: u64, obs_id: u64, kind: u32, cover_bps: u32) {
    let topics = (symbol_short!("obs_att"), job_id);
    env.events().publish(topics, (obs_id, kind, cover_bps));
}

pub fn emit_completion_finalized(
    env: &Env,
    job_id: u64,
    paid_to_worker: i128,
    refunded_to_farmer: i128,
) {
    let topics = (symbol_short!("comp_fin"), job_id);
    env.events().publish(topics, (paid_to_worker, refunded_to_farmer));
}

pub fn emit_followup_finalized(
    env: &Env,
    job_id: u64,
    retained_paid_to_worker: i128,
    refunded_to_farmer: i128,
) {
    let topics = (symbol_short!("fol_fin"), job_id);
    env.events().publish(topics, (retained_paid_to_worker, refunded_to_farmer));
}

pub fn emit_job_disputed(env: &Env, job_id: u64, disputer: &Address) {
    let topics = (symbol_short!("job_disp"), job_id);
    env.events().publish(topics, disputer.clone());
}

pub fn emit_dispute_resolved(env: &Env, job_id: u64, outcome: DisputeOutcome) {
    let topics = (symbol_short!("disp_res"), job_id);
    env.events().publish(topics, outcome);
}

pub fn emit_job_cancelled(env: &Env, job_id: u64) {
    let topics = (symbol_short!("job_canc"), job_id);
    env.events().publish(topics, ());
}

pub fn emit_job_expired_reclaimed(env: &Env, job_id: u64) {
    let topics = (symbol_short!("job_exp"), job_id);
    env.events().publish(topics, ());
}
