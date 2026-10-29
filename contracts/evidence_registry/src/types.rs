use soroban_sdk::{contracttype, Address, BytesN, Vec};

#[contracttype]
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u32)]
pub enum DeviceStatus {
    Active = 0,
    Revoked = 1,
}

#[contracttype]
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DeviceRecord {
    pub public_key: BytesN<32>,
    pub status: DeviceStatus,
    pub registered_at: u64,
}

#[contracttype]
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AttesterRecord {
    pub active: bool,
    pub added_at: u64,
}

#[contracttype]
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AllowedAnalyzer {
    pub metric_id: u32,
    pub family_id: u32,
    pub active: bool,
}

#[contracttype]
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ChallengeRecord {
    pub device_id: BytesN<32>,
    pub job_ref: u64,
    pub kind: u32,
    pub issued_at: u64,
    pub expires_at: u64,
    pub used: bool,
}

#[contracttype]
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AnalysisSubmission {
    pub analyzer_hash: BytesN<32>,
    pub value_bps: u32,
}

#[contracttype]
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AnalysisRecord {
    pub attester: Address,
    pub analyzer_hash: BytesN<32>,
    pub family_id: u32,
    pub value_bps: u32,
    pub recorded_at: u64,
}

#[contracttype]
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u32)]
pub enum ObservationStatus {
    PendingQuorum = 0,
    Accepted = 1,
    Divergent = 2,
}

#[contracttype]
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Observation {
    pub obs_id: u64,
    pub job_ref: u64,
    pub kind: u32,
    pub device_id: BytesN<32>,
    pub image_hash: BytesN<32>,
    pub roi_hash: BytesN<32>,
    pub metric_id: u32,
    pub timestamp: u64,
    pub analyses: Vec<AnalysisRecord>,
    pub status: ObservationStatus,
    pub accepted_value_bps: Option<u32>,
}

#[contracttype]
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RegistryConfig {
    pub timestamp_tolerance_secs: u64,
    pub challenge_ttl_secs: u64,
    pub max_divergence_bps: u32,
    pub quorum: u32,
}
