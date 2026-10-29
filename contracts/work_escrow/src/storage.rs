use soroban_sdk::{contracttype, Address, Env};

use crate::types::Job;

pub const PERSISTENT_BUMP_THRESHOLD: u32 = 17_280;
pub const PERSISTENT_EXTEND_TO: u32 = 120_960;
pub const INSTANCE_BUMP_THRESHOLD: u32 = 17_280;
pub const INSTANCE_EXTEND_TO: u32 = 120_960;

#[contracttype]
#[derive(Clone)]
pub enum DataKey {
    Admin,
    RegistryAddress,
    NextJobId,
    Job(u64),
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

pub fn get_registry_address(env: &Env) -> Option<Address> {
    extend_instance_ttl(env);
    env.storage().instance().get(&DataKey::RegistryAddress)
}

pub fn set_registry_address(env: &Env, reg: &Address) {
    env.storage().instance().set(&DataKey::RegistryAddress, reg);
    extend_instance_ttl(env);
}

pub fn get_next_job_id(env: &Env) -> u64 {
    extend_instance_ttl(env);
    env.storage().instance().get(&DataKey::NextJobId).unwrap_or(1)
}

pub fn increment_job_id(env: &Env) -> u64 {
    let id = get_next_job_id(env);
    env.storage().instance().set(&DataKey::NextJobId, &(id + 1));
    extend_instance_ttl(env);
    id
}

pub fn get_job(env: &Env, job_id: u64) -> Option<Job> {
    let key = DataKey::Job(job_id);
    if env.storage().persistent().has(&key) {
        extend_persistent_ttl(env, &key);
        env.storage().persistent().get(&key)
    } else {
        None
    }
}

pub fn set_job(env: &Env, job_id: u64, job: &Job) {
    let key = DataKey::Job(job_id);
    env.storage().persistent().set(&key, job);
    extend_persistent_ttl(env, &key);
}
