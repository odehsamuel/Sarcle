#![cfg(test)]

use crate::{
    error::RegistryError,
    types::{AnalysisSubmission, DeviceStatus, ObservationStatus, RegistryConfig},
    EvidenceRegistry, EvidenceRegistryClient,
};
use soroban_sdk::{
    testutils::{Address as _, BytesN as _, Ledger},
    Address, Bytes, BytesN, Env,
};

fn hex_to_32(hex_str: &str) -> [u8; 32] {
    let mut arr = [0u8; 32];
    let bytes = hex_str.as_bytes();
    for i in 0..32 {
        let hi = hex_nibble(bytes[i * 2]);
        let lo = hex_nibble(bytes[i * 2 + 1]);
        arr[i] = (hi << 4) | lo;
    }
    arr
}

fn hex_to_16(hex_str: &str) -> [u8; 16] {
    let mut arr = [0u8; 16];
    let bytes = hex_str.as_bytes();
    for i in 0..16 {
        let hi = hex_nibble(bytes[i * 2]);
        let lo = hex_nibble(bytes[i * 2 + 1]);
        arr[i] = (hi << 4) | lo;
    }
    arr
}

fn hex_to_64(hex_str: &str) -> [u8; 64] {
    let mut arr = [0u8; 64];
    let bytes = hex_str.as_bytes();
    for i in 0..64 {
        let hi = hex_nibble(bytes[i * 2]);
        let lo = hex_nibble(bytes[i * 2 + 1]);
        arr[i] = (hi << 4) | lo;
    }
    arr
}

fn hex_nibble(b: u8) -> u8 {
    match b {
        b'0'..=b'9' => b - b'0',
        b'a'..=b'f' => b - b'a' + 10,
        b'A'..=b'F' => b - b'A' + 10,
        _ => panic!("invalid hex"),
    }
}

fn setup_registry() -> (
    Env,
    EvidenceRegistryClient<'static>,
    Address,
    Address,
    Address,
    BytesN<32>,
    BytesN<32>,
    BytesN<32>,
) {
    let env = Env::default();
    env.mock_all_auths();
    env.ledger().set_timestamp(1700000000);

    let contract_id = env.register(EvidenceRegistry, ());
    let client = EvidenceRegistryClient::new(&env, &contract_id);

    let admin = Address::generate(&env);
    let attester_a = Address::generate(&env);
    let attester_b = Address::generate(&env);

    let config = RegistryConfig {
        timestamp_tolerance_secs: 60,
        challenge_ttl_secs: 300,
        max_divergence_bps: 500, // 5%
        quorum: 2,
    };
    client.init(&admin, &config);

    // Register Attesters
    client.add_attester(&admin, &attester_a);
    client.add_attester(&admin, &attester_b);

    // Allowlist Analyzers
    // Analyzer 1: Metric 1 (ExG), Family 1 (Python)
    let analyzer_1 = BytesN::from_array(&env, &[1u8; 32]);
    client.allow_analyzer(&admin, &analyzer_1, &1, &1);

    // Analyzer 2: Metric 1 (ExG), Family 2 (Rust)
    let analyzer_2 = BytesN::from_array(&env, &[2u8; 32]);
    client.allow_analyzer(&admin, &analyzer_2, &1, &2);

    // Register test vector Device A
    let dev_a_bytes = hex_to_32("7e33a71be43d3f3925e08b7e0d9861547812ae4b66393c9a86022efd2087a3a3");
    let device_id = BytesN::from_array(&env, &dev_a_bytes);
    client.register_device(&admin, &device_id);

    (
        env, client, admin, attester_a, attester_b, device_id, analyzer_1, analyzer_2,
    )
}

#[test]
fn test_initialization_and_admin() {
    let (env, client, admin, _, _, device_id, _, _) = setup_registry();

    let config = RegistryConfig {
        timestamp_tolerance_secs: 60,
        challenge_ttl_secs: 300,
        max_divergence_bps: 500,
        quorum: 2,
    };
    assert_eq!(
        client.try_init(&admin, &config).unwrap_err().unwrap(),
        RegistryError::AlreadyInitialized
    );

    let dev = client.get_device(&device_id);
    assert_eq!(dev.status, DeviceStatus::Active);

    client.revoke_device(&admin, &device_id);
    let dev_revoked = client.get_device(&device_id);
    assert_eq!(dev_revoked.status, DeviceStatus::Revoked);
}

#[test]
fn test_challenge_request_and_expiry() {
    let (env, client, _, attester_a, _, device_id, _, _) = setup_registry();

    let chal = client.request_challenge(&attester_a, &1001, &device_id, &0);

    // Advance past TTL (300 secs)
    env.ledger().set_timestamp(1700000000 + 301);

    let dummy_img = BytesN::from_array(&env, &[9u8; 32]);
    let dummy_roi = BytesN::from_array(&env, &[8u8; 32]);
    let dummy_sig = BytesN::from_array(&env, &[0u8; 64]);
    let an_sub = AnalysisSubmission {
        analyzer_hash: BytesN::from_array(&env, &[1u8; 32]),
        value_bps: 4500,
    };

    let res = client.try_submit_observation(
        &attester_a,
        &1001,
        &0,
        &dummy_img,
        &dummy_roi,
        &1,
        &chal,
        &1,
        &1700000010,
        &dummy_sig,
        &an_sub,
    );
    assert_eq!(res.unwrap_err().unwrap(), RegistryError::ChallengeExpired);
}

#[test]
fn test_challenge_mismatch() {
    let (env, client, _, attester_a, _, device_id, _, _) = setup_registry();

    let chal = client.request_challenge(&attester_a, &1001, &device_id, &0);

    let dummy_img = BytesN::from_array(&env, &[9u8; 32]);
    let dummy_roi = BytesN::from_array(&env, &[8u8; 32]);
    let dummy_sig = BytesN::from_array(&env, &[0u8; 64]);
    let an_sub = AnalysisSubmission {
        analyzer_hash: BytesN::from_array(&env, &[1u8; 32]),
        value_bps: 4500,
    };

    let res = client.try_submit_observation(
        &attester_a,
        &1002, // mismatch job_ref
        &0,
        &dummy_img,
        &dummy_roi,
        &1,
        &chal,
        &1,
        &1700000010,
        &dummy_sig,
        &an_sub,
    );
    assert_eq!(res.unwrap_err().unwrap(), RegistryError::ChallengeMismatch);
}

#[test]
fn test_shared_test_vector_1_and_replay_protection() {
    let (env, client, _, attester_a, _, device_id, analyzer_1, _) = setup_registry();

    // Load Vector 1:
    let chal_bytes = hex_to_16("11223344556677889900aabbccddeeff");
    let challenge = BytesN::from_array(&env, &chal_bytes);

    // Inject challenge record manually into registry storage for exact vector replay test
    let chal_record = crate::types::ChallengeRecord {
        device_id: device_id.clone(),
        job_ref: 1001,
        kind: 0,
        issued_at: 1700000000,
        expires_at: 1700000300,
        used: false,
    };
    crate::storage::set_challenge(&env, &challenge, &chal_record);

    let img_bytes = hex_to_32("fdc39e1df3312f071d33c370528f5311a00cc3d76d8d17468f74672c0f0e32e2");
    let image_hash = BytesN::from_array(&env, &img_bytes);
    let roi_hash = BytesN::from_array(&env, &[4u8; 32]);

    let sig_bytes = hex_to_64("4e39d561fb03a6b02f988ee1a62b08ee1722589540ad380f2d08aba1c9c58f1d0e2a68772b0c646e62336a7d6ee528fa8c875b3cd3ba1c827b32f1e078b19f07");
    let signature = BytesN::from_array(&env, &sig_bytes);

    let an_sub = AnalysisSubmission {
        analyzer_hash: analyzer_1.clone(),
        value_bps: 6500,
    };

    // First submission: Must succeed
    let obs_id = client.submit_observation(
        &attester_a,
        &1001,
        &0,
        &image_hash,
        &roi_hash,
        &1,
        &challenge,
        &1,
        &1700000000,
        &signature,
        &an_sub,
    );
    assert_eq!(obs_id, 1);
    assert_eq!(client.last_counter(&device_id), 1);

    // Second submission with same challenge: Must fail (ChallengeAlreadyUsed)
    let res_replay = client.try_submit_observation(
        &attester_a,
        &1001,
        &0,
        &image_hash,
        &roi_hash,
        &1,
        &challenge,
        &2,
        &1700000000,
        &signature,
        &an_sub,
    );
    assert_eq!(
        res_replay.unwrap_err().unwrap(),
        RegistryError::ChallengeAlreadyUsed
    );
}

#[test]
fn test_quorum_agreement_boundaries() {
    let (env, client, admin, attester_a, attester_b, device_id, analyzer_1, analyzer_2) =
        setup_registry();

    // 1. Submit initial observation with Analysis A = 5000 bps
    let chal_1_bytes = hex_to_16("11223344556677889900aabbccddeeff");
    let chal_1 = BytesN::from_array(&env, &chal_1_bytes);
    let chal_record_1 = crate::types::ChallengeRecord {
        device_id: device_id.clone(),
        job_ref: 2001,
        kind: 0,
        issued_at: 1700000000,
        expires_at: 1700000300,
        used: false,
    };
    crate::storage::set_challenge(&env, &chal_1, &chal_record_1);

    let img_bytes = hex_to_32("fdc39e1df3312f071d33c370528f5311a00cc3d76d8d17468f74672c0f0e32e2");
    let image_hash = BytesN::from_array(&env, &img_bytes);
    let roi_hash = BytesN::from_array(&env, &[4u8; 32]);
    let sig_bytes = hex_to_64("4e39d561fb03a6b02f988ee1a62b08ee1722589540ad380f2d08aba1c9c58f1d0e2a68772b0c646e62336a7d6ee528fa8c875b3cd3ba1c827b32f1e078b19f07");
    let signature = BytesN::from_array(&env, &sig_bytes);

    // Wait! Vector 1 signature was for job_ref = 1001, so let's use job_ref 1001
    let chal_record_valid = crate::types::ChallengeRecord {
        device_id: device_id.clone(),
        job_ref: 1001,
        kind: 0,
        issued_at: 1700000000,
        expires_at: 1700000300,
        used: false,
    };
    crate::storage::set_challenge(&env, &chal_1, &chal_record_valid);

    let obs_id = client.submit_observation(
        &attester_a,
        &1001,
        &0,
        &image_hash,
        &roi_hash,
        &1,
        &chal_1,
        &1,
        &1700000000,
        &signature,
        &AnalysisSubmission {
            analyzer_hash: analyzer_1.clone(),
            value_bps: 5000,
        },
    );

    // Initial state: PendingQuorum
    let obs = client.get_observation(&obs_id);
    assert_eq!(obs.status, ObservationStatus::PendingQuorum);
    assert_eq!(obs.accepted_value_bps, None);

    // Try adding analysis with same attester -> DuplicateAttesterAnalysis
    let res_dup_attester = client.try_add_analysis(&attester_a, &obs_id, &analyzer_2, &5200);
    assert_eq!(
        res_dup_attester.unwrap_err().unwrap(),
        RegistryError::DuplicateAttesterAnalysis
    );

    // Allow a different analyzer but with same family (Family 1)
    let analyzer_same_family = BytesN::from_array(&env, &[99u8; 32]);
    client.allow_analyzer(&admin, &analyzer_same_family, &1, &1); // family 1

    let res_dup_family =
        client.try_add_analysis(&attester_b, &obs_id, &analyzer_same_family, &5200);
    assert_eq!(
        res_dup_family.unwrap_err().unwrap(),
        RegistryError::DuplicateFamilyAnalysis
    );

    // Boundary Test Case 1: Exactly at tolerance (5000 + 500 = 5500 bps)
    client.add_analysis(&attester_b, &obs_id, &analyzer_2, &5500);

    let obs_final = client.get_observation(&obs_id);
    assert_eq!(obs_final.status, ObservationStatus::Accepted);
    assert_eq!(obs_final.accepted_value_bps, Some(5250)); // (5000 + 5500) / 2
}

#[test]
fn test_quorum_divergence_one_point_over() {
    let (env, client, _, attester_a, attester_b, device_id, analyzer_1, analyzer_2) =
        setup_registry();

    let chal_1_bytes = hex_to_16("11223344556677889900aabbccddeeff");
    let chal_1 = BytesN::from_array(&env, &chal_1_bytes);
    let chal_record = crate::types::ChallengeRecord {
        device_id: device_id.clone(),
        job_ref: 1001,
        kind: 0,
        issued_at: 1700000000,
        expires_at: 1700000300,
        used: false,
    };
    crate::storage::set_challenge(&env, &chal_1, &chal_record);

    let img_bytes = hex_to_32("fdc39e1df3312f071d33c370528f5311a00cc3d76d8d17468f74672c0f0e32e2");
    let image_hash = BytesN::from_array(&env, &img_bytes);
    let roi_hash = BytesN::from_array(&env, &[4u8; 32]);
    let sig_bytes = hex_to_64("4e39d561fb03a6b02f988ee1a62b08ee1722589540ad380f2d08aba1c9c58f1d0e2a68772b0c646e62336a7d6ee528fa8c875b3cd3ba1c827b32f1e078b19f07");
    let signature = BytesN::from_array(&env, &sig_bytes);

    let obs_id = client.submit_observation(
        &attester_a,
        &1001,
        &0,
        &image_hash,
        &roi_hash,
        &1,
        &chal_1,
        &1,
        &1700000000,
        &signature,
        &AnalysisSubmission {
            analyzer_hash: analyzer_1.clone(),
            value_bps: 5000,
        },
    );

    // Boundary Test Case 2: One basis point over tolerance (5000 + 501 = 5501 bps)
    client.add_analysis(&attester_b, &obs_id, &analyzer_2, &5501);

    let obs_final = client.get_observation(&obs_id);
    assert_eq!(obs_final.status, ObservationStatus::Divergent);
    assert_eq!(obs_final.accepted_value_bps, None);
}
