#![no_std]

pub mod error;
pub mod events;
pub mod storage;
pub mod types;

#[cfg(test)]
mod test;

use error::RegistryError;
use soroban_sdk::{
    contract, contractimpl, Address, Bytes, BytesN, Env, Vec,
};
use types::{
    AllowedAnalyzer, AnalysisRecord, AnalysisSubmission, AttesterRecord, ChallengeRecord,
    DeviceRecord, DeviceStatus, Observation, ObservationStatus, RegistryConfig,
};

pub const DOMAIN_TAG: &[u8] = b"PoW-OBS-v2"; // Exactly 10 bytes
pub const CANONICAL_MESSAGE_LEN: u32 = 115;

#[contract]
pub struct EvidenceRegistry;

#[contractimpl]
impl EvidenceRegistry {
    /// Initialize the evidence registry with admin address and system configuration.
    pub fn init(env: Env, admin: Address, config: RegistryConfig) -> Result<(), RegistryError> {
        if storage::get_admin(&env).is_some() {
            return Err(RegistryError::AlreadyInitialized);
        }
        if config.quorum < 1 || config.max_divergence_bps > 10000 {
            return Err(RegistryError::ConfigError);
        }

        storage::set_admin(&env, &admin);
        storage::set_config(&env, &config);
        Ok(())
    }

    /// Admin: Register an authorized edge camera device by its Ed25519 public key.
    pub fn register_device(
        env: Env,
        admin: Address,
        device_id: BytesN<32>,
    ) -> Result<(), RegistryError> {
        admin.require_auth();
        Self::assert_admin(&env, &admin)?;

        if storage::get_device(&env, &device_id).is_some() {
            return Err(RegistryError::DeviceAlreadyRegistered);
        }

        let record = DeviceRecord {
            public_key: device_id.clone(),
            status: DeviceStatus::Active,
            registered_at: env.ledger().timestamp(),
        };
        storage::set_device(&env, &device_id, &record);
        events::emit_device_registered(&env, &device_id);
        Ok(())
    }

    /// Admin: Revoke an edge camera device (e.g., if physically compromised or decommissioned).
    pub fn revoke_device(
        env: Env,
        admin: Address,
        device_id: BytesN<32>,
    ) -> Result<(), RegistryError> {
        admin.require_auth();
        Self::assert_admin(&env, &admin)?;

        let mut record = storage::get_device(&env, &device_id).ok_or(RegistryError::DeviceNotFound)?;
        record.status = DeviceStatus::Revoked;
        storage::set_device(&env, &device_id, &record);
        events::emit_device_revoked(&env, &device_id);
        Ok(())
    }

    /// Admin: Add an authorized attester address.
    pub fn add_attester(env: Env, admin: Address, attester: Address) -> Result<(), RegistryError> {
        admin.require_auth();
        Self::assert_admin(&env, &admin)?;

        let record = AttesterRecord {
            active: true,
            added_at: env.ledger().timestamp(),
        };
        storage::set_attester(&env, &attester, &record);
        events::emit_attester_added(&env, &attester);
        Ok(())
    }

    /// Admin: Deactivate an attester address.
    pub fn remove_attester(
        env: Env,
        admin: Address,
        attester: Address,
    ) -> Result<(), RegistryError> {
        admin.require_auth();
        Self::assert_admin(&env, &admin)?;

        let mut record =
            storage::get_attester(&env, &attester).ok_or(RegistryError::AttesterNotFound)?;
        record.active = false;
        storage::set_attester(&env, &attester, &record);
        events::emit_attester_removed(&env, &attester);
        Ok(())
    }

    /// Admin: Allowlist a deterministic CV analyzer hash for a specific metric and algorithm family.
    pub fn allow_analyzer(
        env: Env,
        admin: Address,
        analyzer_hash: BytesN<32>,
        metric_id: u32,
        family_id: u32,
    ) -> Result<(), RegistryError> {
        admin.require_auth();
        Self::assert_admin(&env, &admin)?;

        let record = AllowedAnalyzer {
            metric_id,
            family_id,
            active: true,
        };
        storage::set_analyzer(&env, &analyzer_hash, &record);
        events::emit_analyzer_allowed(&env, &analyzer_hash, metric_id, family_id);
        Ok(())
    }

    /// Admin: Revoke an analyzer hash.
    pub fn revoke_analyzer(
        env: Env,
        admin: Address,
        analyzer_hash: BytesN<32>,
    ) -> Result<(), RegistryError> {
        admin.require_auth();
        Self::assert_admin(&env, &admin)?;

        let mut record =
            storage::get_analyzer(&env, &analyzer_hash).ok_or(RegistryError::AnalyzerNotAllowed)?;
        record.active = false;
        storage::set_analyzer(&env, &analyzer_hash, &record);
        events::emit_analyzer_revoked(&env, &analyzer_hash);
        Ok(())
    }

    /// Request a challenge nonce for an edge capture.
    ///
    /// Caveat on Soroban PRNG:
    /// Soroban's env.prng() provides protocol-level pseudo-random numbers derived from the ledger seed.
    /// For Proof-of-Weeding, the challenge requires freshness, unpredictability prior to ledger inclusion,
    /// and uniqueness to prevent pre-recorded image playback. It is NOT intended as high-stakes lottery randomness.
    pub fn request_challenge(
        env: Env,
        attester: Address,
        job_ref: u64,
        device_id: BytesN<32>,
        kind: u32,
    ) -> Result<BytesN<16>, RegistryError> {
        attester.require_auth();
        Self::assert_active_attester(&env, &attester)?;

        let device = storage::get_device(&env, &device_id).ok_or(RegistryError::DeviceNotFound)?;
        if device.status != DeviceStatus::Active {
            return Err(RegistryError::DeviceRevoked);
        }
        if kind > 2 {
            return Err(RegistryError::InvalidObservationKind);
        }

        let config = storage::get_config(&env).ok_or(RegistryError::NotInitialized)?;
        let now = env.ledger().timestamp();
        let challenge: BytesN<16> = env.prng().gen();

        let record = ChallengeRecord {
            device_id: device_id.clone(),
            job_ref,
            kind,
            issued_at: now,
            expires_at: now + config.challenge_ttl_secs,
            used: false,
        };
        storage::set_challenge(&env, &challenge, &record);
        events::emit_challenge_issued(&env, &device_id, job_ref, kind, &challenge);

        Ok(challenge)
    }

    /// Submit a hardware-signed observation frame along with the primary attester's analysis.
    pub fn submit_observation(
        env: Env,
        attester: Address,
        job_ref: u64,
        kind: u32,
        image_hash: BytesN<32>,
        roi_hash: BytesN<32>,
        metric_id: u32,
        challenge: BytesN<16>,
        counter: u64,
        timestamp: u64,
        signature: BytesN<64>,
        analysis: AnalysisSubmission,
    ) -> Result<u64, RegistryError> {
        attester.require_auth();
        Self::assert_active_attester(&env, &attester)?;

        if kind > 2 {
            return Err(RegistryError::InvalidObservationKind);
        }
        if analysis.value_bps > 10000 {
            return Err(RegistryError::InvalidMetricValue);
        }

        let config = storage::get_config(&env).ok_or(RegistryError::NotInitialized)?;
        let now = env.ledger().timestamp();

        // 1. Verify Challenge
        let mut chal_record =
            storage::get_challenge(&env, &challenge).ok_or(RegistryError::ChallengeNotFound)?;
        if chal_record.used {
            return Err(RegistryError::ChallengeAlreadyUsed);
        }
        if now > chal_record.expires_at {
            return Err(RegistryError::ChallengeExpired);
        }
        if chal_record.job_ref != job_ref || chal_record.kind != kind {
            return Err(RegistryError::ChallengeMismatch);
        }

        // 2. Verify Device
        let device_id = chal_record.device_id.clone();
        let device = storage::get_device(&env, &device_id).ok_or(RegistryError::DeviceNotFound)?;
        if device.status != DeviceStatus::Active {
            return Err(RegistryError::DeviceRevoked);
        }

        // 3. Verify Timestamp Tolerance
        let tol = config.timestamp_tolerance_secs;
        if timestamp + tol < chal_record.issued_at || timestamp > chal_record.expires_at + tol {
            return Err(RegistryError::TimestampOutOfRange);
        }

        // 4. Verify Monotonic Counter
        let last_counter = storage::get_last_counter(&env, &device_id);
        if counter <= last_counter {
            return Err(RegistryError::CounterNotIncreasing);
        }

        // 5. Verify Analyzer
        let analyzer = storage::get_analyzer(&env, &analysis.analyzer_hash)
            .ok_or(RegistryError::AnalyzerNotAllowed)?;
        if !analyzer.active || analyzer.metric_id != metric_id {
            return Err(RegistryError::AnalyzerNotAllowed);
        }

        // 6. Verify Ed25519 Hardware Signature over exact 115 canonical bytes
        let message_bytes = Self::build_canonical_message(
            &env,
            &device_id,
            job_ref,
            kind,
            counter,
            timestamp,
            &challenge,
            &image_hash,
        );
        env.crypto()
            .ed25519_verify(&device_id, &message_bytes, &signature);

        // Mark challenge used and record monotonic counter
        chal_record.used = true;
        storage::set_challenge(&env, &challenge, &chal_record);
        storage::set_last_counter(&env, &device_id, counter);

        // Build Initial Observation Record
        let obs_id = storage::increment_obs_id(&env);
        let mut analyses = Vec::new(&env);
        analyses.push_back(AnalysisRecord {
            attester: attester.clone(),
            analyzer_hash: analysis.analyzer_hash.clone(),
            family_id: analyzer.family_id,
            value_bps: analysis.value_bps,
            recorded_at: now,
        });

        let (status, accepted_val) = if config.quorum == 1 {
            (ObservationStatus::Accepted, Some(analysis.value_bps))
        } else {
            (ObservationStatus::PendingQuorum, None)
        };

        let obs = Observation {
            obs_id,
            job_ref,
            kind,
            device_id: device_id.clone(),
            image_hash: image_hash.clone(),
            roi_hash: roi_hash.clone(),
            metric_id,
            timestamp,
            analyses,
            status,
            accepted_value_bps: accepted_val,
        };
        storage::set_observation(&env, obs_id, &obs);

        events::emit_observation_submitted(&env, obs_id, job_ref, kind, &device_id);
        events::emit_analysis_added(
            &env,
            obs_id,
            &attester,
            &analysis.analyzer_hash,
            analysis.value_bps,
        );
        if let Some(val) = accepted_val {
            events::emit_observation_accepted(&env, obs_id, val);
        }

        Ok(obs_id)
    }

    /// Submit an independent analysis from a distinct attester and analyzer family.
    pub fn add_analysis(
        env: Env,
        attester: Address,
        obs_id: u64,
        analyzer_hash: BytesN<32>,
        value_bps: u32,
    ) -> Result<(), RegistryError> {
        attester.require_auth();
        Self::assert_active_attester(&env, &attester)?;

        if value_bps > 10000 {
            return Err(RegistryError::InvalidMetricValue);
        }

        let mut obs = storage::get_observation(&env, obs_id)
            .ok_or(RegistryError::ObservationNotFound)?;
        if obs.status != ObservationStatus::PendingQuorum {
            return Err(RegistryError::ObservationAlreadyQuorum);
        }

        let analyzer = storage::get_analyzer(&env, &analyzer_hash)
            .ok_or(RegistryError::AnalyzerNotAllowed)?;
        if !analyzer.active || analyzer.metric_id != obs.metric_id {
            return Err(RegistryError::AnalyzerNotAllowed);
        }

        // Independence rule: Must have distinct attester and distinct family_id
        for existing in obs.analyses.iter() {
            if existing.attester == attester {
                return Err(RegistryError::DuplicateAttesterAnalysis);
            }
            if existing.family_id == analyzer.family_id {
                return Err(RegistryError::DuplicateFamilyAnalysis);
            }
        }

        let now = env.ledger().timestamp();
        obs.analyses.push_back(AnalysisRecord {
            attester: attester.clone(),
            analyzer_hash: analyzer_hash.clone(),
            family_id: analyzer.family_id,
            value_bps,
            recorded_at: now,
        });

        events::emit_analysis_added(&env, obs_id, &attester, &analyzer_hash, value_bps);

        let config = storage::get_config(&env).ok_or(RegistryError::NotInitialized)?;
        if obs.analyses.len() >= config.quorum {
            let first_val = obs.analyses.get(0).unwrap().value_bps;
            let second_val = obs.analyses.get(1).unwrap().value_bps;
            let diff = if first_val > second_val {
                first_val - second_val
            } else {
                second_val - first_val
            };

            if diff <= config.max_divergence_bps {
                let mean = (first_val + second_val) / 2;
                obs.status = ObservationStatus::Accepted;
                obs.accepted_value_bps = Some(mean);
                events::emit_observation_accepted(&env, obs_id, mean);
            } else {
                obs.status = ObservationStatus::Divergent;
                obs.accepted_value_bps = None;
                events::emit_observation_divergent(&env, obs_id, diff);
            }
        }

        storage::set_observation(&env, obs_id, &obs);
        Ok(())
    }

    // --- Views ---

    pub fn get_observation(env: Env, obs_id: u64) -> Result<Observation, RegistryError> {
        storage::get_observation(&env, obs_id).ok_or(RegistryError::ObservationNotFound)
    }

    pub fn get_device(env: Env, device_id: BytesN<32>) -> Result<DeviceRecord, RegistryError> {
        storage::get_device(&env, &device_id).ok_or(RegistryError::DeviceNotFound)
    }

    pub fn is_analyzer_allowed(env: Env, analyzer_hash: BytesN<32>, metric_id: u32) -> bool {
        if let Some(an) = storage::get_analyzer(&env, &analyzer_hash) {
            an.active && an.metric_id == metric_id
        } else {
            false
        }
    }

    pub fn is_attester(env: Env, attester: Address) -> bool {
        if let Some(att) = storage::get_attester(&env, &attester) {
            att.active
        } else {
            false
        }
    }

    pub fn last_counter(env: Env, device_id: BytesN<32>) -> u64 {
        storage::get_last_counter(&env, &device_id)
    }

    // --- Internal Helpers ---

    fn assert_admin(env: &Env, admin: &Address) -> Result<(), RegistryError> {
        let current = storage::get_admin(env).ok_or(RegistryError::NotInitialized)?;
        if current != *admin {
            return Err(RegistryError::Unauthorized);
        }
        Ok(())
    }

    fn assert_active_attester(env: &Env, attester: &Address) -> Result<(), RegistryError> {
        let record =
            storage::get_attester(env, attester).ok_or(RegistryError::AttesterNotFound)?;
        if !record.active {
            return Err(RegistryError::AttesterNotActive);
        }
        Ok(())
    }

    pub fn build_canonical_message(
        env: &Env,
        device_id: &BytesN<32>,
        job_ref: u64,
        kind: u32,
        counter: u64,
        timestamp: u64,
        challenge: &BytesN<16>,
        image_hash: &BytesN<32>,
    ) -> Bytes {
        let mut msg = Bytes::new(env);
        msg.extend_from_slice(DOMAIN_TAG);
        msg.extend_from_slice(&device_id.to_array());
        msg.extend_from_slice(&job_ref.to_be_bytes());
        msg.extend_from_slice(&(kind as u8).to_be_bytes());
        msg.extend_from_slice(&counter.to_be_bytes());
        msg.extend_from_slice(&timestamp.to_be_bytes());
        msg.extend_from_slice(&challenge.to_array());
        msg.extend_from_slice(&image_hash.to_array());
        msg
    }
}
