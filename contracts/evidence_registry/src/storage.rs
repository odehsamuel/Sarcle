use soroban_sdk::{contracttype, Address, BytesN, Env};

use crate::types::{
    AllowedAnalyzer, AttesterRecord, ChallengeRecord, DeviceRecord, Observation, RegistryConfig,
};

// Storage TTL Policy constants (Stellar ledger close time is ~5s):
// BUMP_THRESHOLD: 17,280 ledgers (~24 hours). If remaining TTL falls below this, extend.
// EXTEND_TO: 120,960 ledgers (~7 days). Target lifetime of live contract entries.
pub const PERSISTENT_BUMP_THRESHOLD: u32 = 17_280;
pub const PERSISTENT_EXTEND_TO: u32 = 120_960;
pub const INSTANCE_BUMP_THRESHOLD: u32 = 17_280;
pub const INSTANCE_EXTEND_TO: u32 = 120_960;

#[contracttype]
#[derive(Clone)]
pub enum DataKey {
    Admin,
    Config,
    NextObsId,
    Device(BytesN<32>),
    Attester(Address),
    Analyzer(BytesN<32>),
    LastCounter(BytesN<32>),
    Challenge(BytesN<16>),
    Observation(u64),
}

pub fn extend_instance_ttl(env: &Env) {
    env.storage()
        .instance()
        .extend_ttl(INSTANCE_BUMP_THRESHOLD, INSTANCE_EXTEND_TO);
}

pub fn extend_persistent_ttl(env: &Env, key: &DataKey) {
    env.storage()
        .persistent()
        .extend_ttl(key, PERSISTENT_BUMP_THRESHOLD, PERSISTENT_EXTEND_TO);
}

pub fn get_admin(env: &Env) -> Option<Address> {
    extend_instance_ttl(env);
    env.storage().instance().get(&DataKey::Admin)
}

pub fn set_admin(env: &Env, admin: &Address) {
    env.storage().instance().set(&DataKey::Admin, admin);
    extend_instance_ttl(env);
}

pub fn get_config(env: &Env) -> Option<RegistryConfig> {
    extend_instance_ttl(env);
    env.storage().instance().get(&DataKey::Config)
}

pub fn set_config(env: &Env, config: &RegistryConfig) {
    env.storage().instance().set(&DataKey::Config, config);
    extend_instance_ttl(env);
}

pub fn get_next_obs_id(env: &Env) -> u64 {
    extend_instance_ttl(env);
    env.storage().instance().get(&DataKey::NextObsId).unwrap_or(1)
}

pub fn increment_obs_id(env: &Env) -> u64 {
    let id = get_next_obs_id(env);
    env.storage().instance().set(&DataKey::NextObsId, &(id + 1));
    extend_instance_ttl(env);
    id
}

pub fn get_device(env: &Env, device_id: &BytesN<32>) -> Option<DeviceRecord> {
    let key = DataKey::Device(device_id.clone());
    if env.storage().persistent().has(&key) {
        extend_persistent_ttl(env, &key);
        env.storage().persistent().get(&key)
    } else {
        None
    }
}

pub fn set_device(env: &Env, device_id: &BytesN<32>, record: &DeviceRecord) {
    let key = DataKey::Device(device_id.clone());
    env.storage().persistent().set(&key, record);
    extend_persistent_ttl(env, &key);
}

pub fn get_attester(env: &Env, attester: &Address) -> Option<AttesterRecord> {
    let key = DataKey::Attester(attester.clone());
    if env.storage().persistent().has(&key) {
        extend_persistent_ttl(env, &key);
        env.storage().persistent().get(&key)
    } else {
        None
    }
}

pub fn set_attester(env: &Env, attester: &Address, record: &AttesterRecord) {
    let key = DataKey::Attester(attester.clone());
    env.storage().persistent().set(&key, record);
    extend_persistent_ttl(env, &key);
}

pub fn get_analyzer(env: &Env, hash: &BytesN<32>) -> Option<AllowedAnalyzer> {
    let key = DataKey::Analyzer(hash.clone());
    if env.storage().persistent().has(&key) {
        extend_persistent_ttl(env, &key);
        env.storage().persistent().get(&key)
    } else {
        None
    }
}

pub fn set_analyzer(env: &Env, hash: &BytesN<32>, record: &AllowedAnalyzer) {
    let key = DataKey::Analyzer(hash.clone());
    env.storage().persistent().set(&key, record);
    extend_persistent_ttl(env, &key);
}

pub fn get_last_counter(env: &Env, device_id: &BytesN<32>) -> u64 {
    let key = DataKey::LastCounter(device_id.clone());
    if env.storage().persistent().has(&key) {
        extend_persistent_ttl(env, &key);
        env.storage().persistent().get(&key).unwrap_or(0)
    } else {
        0
    }
}

pub fn set_last_counter(env: &Env, device_id: &BytesN<32>, counter: u64) {
    let key = DataKey::LastCounter(device_id.clone());
    env.storage().persistent().set(&key, &counter);
    extend_persistent_ttl(env, &key);
}

pub fn get_challenge(env: &Env, challenge: &BytesN<16>) -> Option<ChallengeRecord> {
    let key = DataKey::Challenge(challenge.clone());
    if env.storage().persistent().has(&key) {
        extend_persistent_ttl(env, &key);
        env.storage().persistent().get(&key)
    } else {
        None
    }
}

pub fn set_challenge(env: &Env, challenge: &BytesN<16>, record: &ChallengeRecord) {
    let key = DataKey::Challenge(challenge.clone());
    env.storage().persistent().set(&key, record);
    extend_persistent_ttl(env, &key);
}

pub fn get_observation(env: &Env, obs_id: u64) -> Option<Observation> {
    let key = DataKey::Observation(obs_id);
    if env.storage().persistent().has(&key) {
        extend_persistent_ttl(env, &key);
        env.storage().persistent().get(&key)
    } else {
        None
    }
}

pub fn set_observation(env: &Env, obs_id: u64, obs: &Observation) {
    let key = DataKey::Observation(obs_id);
    env.storage().persistent().set(&key, obs);
    extend_persistent_ttl(env, &key);
}
