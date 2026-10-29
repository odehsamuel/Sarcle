use soroban_sdk::{symbol_short, Address, BytesN, Env, Symbol};

pub fn emit_device_registered(env: &Env, device_id: &BytesN<32>) {
    let topics = (symbol_short!("dev_reg"), device_id.clone());
    env.events().publish(topics, ());
}

pub fn emit_device_revoked(env: &Env, device_id: &BytesN<32>) {
    let topics = (symbol_short!("dev_rev"), device_id.clone());
    env.events().publish(topics, ());
}

pub fn emit_attester_added(env: &Env, attester: &Address) {
    let topics = (symbol_short!("att_add"), attester.clone());
    env.events().publish(topics, ());
}

pub fn emit_attester_removed(env: &Env, attester: &Address) {
    let topics = (symbol_short!("att_rem"), attester.clone());
    env.events().publish(topics, ());
}

pub fn emit_analyzer_allowed(env: &Env, hash: &BytesN<32>, metric_id: u32, family_id: u32) {
    let topics = (symbol_short!("an_allow"), hash.clone());
    env.events().publish(topics, (metric_id, family_id));
}

pub fn emit_analyzer_revoked(env: &Env, hash: &BytesN<32>) {
    let topics = (symbol_short!("an_rev"), hash.clone());
    env.events().publish(topics, ());
}

pub fn emit_challenge_issued(
    env: &Env,
    device_id: &BytesN<32>,
    job_ref: u64,
    kind: u32,
    challenge: &BytesN<16>,
) {
    let topics = (symbol_short!("chal_iss"), device_id.clone());
    env.events().publish(topics, (job_ref, kind, challenge.clone()));
}

pub fn emit_observation_submitted(
    env: &Env,
    obs_id: u64,
    job_ref: u64,
    kind: u32,
    device_id: &BytesN<32>,
) {
    let topics = (symbol_short!("obs_sub"), obs_id);
    env.events().publish(topics, (job_ref, kind, device_id.clone()));
}

pub fn emit_analysis_added(
    env: &Env,
    obs_id: u64,
    attester: &Address,
    analyzer_hash: &BytesN<32>,
    value_bps: u32,
) {
    let topics = (symbol_short!("an_add"), obs_id);
    env.events().publish(topics, (attester.clone(), analyzer_hash.clone(), value_bps));
}

pub fn emit_observation_accepted(env: &Env, obs_id: u64, accepted_value_bps: u32) {
    let topics = (symbol_short!("obs_acc"), obs_id);
    env.events().publish(topics, accepted_value_bps);
}

pub fn emit_observation_divergent(env: &Env, obs_id: u64, divergence_bps: u32) {
    let topics = (symbol_short!("obs_div"), obs_id);
    env.events().publish(topics, divergence_bps);
}
