use soroban_sdk::{contracttype, Address, BytesN};

#[contracttype]
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u32)]
pub enum JobState {
    Funded = 0,
    BaselineRecorded = 1,
    CompletionRecorded = 2,
    CompletionPaid = 3,
    Refunded = 4,
    FollowupRecorded = 5,
    Settled = 6,
    Disputed = 7,
    Resolved = 8,
}

#[contracttype]
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u32)]
pub enum DisputeOutcome {
    FarmerWins = 0,
    WorkerWins = 1,
    Split = 2,
}

#[contracttype]
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CreateJobParams {
    pub farmer: Address,
    pub worker: Address,
    pub token: Address,
    pub amount: i128,
    pub device_id: BytesN<32>,
    pub roi_hash: BytesN<32>,
    pub metric_id: u32,
    pub arbiter: Address,
    pub threshold_bps: u32,
    pub min_baseline_bps: u32,
    pub retainage_bps: u32,
    pub followup_delay_secs: u64,
    pub max_regrowth_bps: u32,
    pub baseline_deadline: u64,
    pub completion_deadline: u64,
    pub followup_deadline: u64,
    pub challenge_window_secs: u64,
}

#[contracttype]
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Job {
    pub job_id: u64,
    pub farmer: Address,
    pub worker: Address,
    pub token: Address,
    pub amount: i128,
    pub device_id: BytesN<32>,
    pub roi_hash: BytesN<32>,
    pub metric_id: u32,
    pub arbiter: Address,
    pub threshold_bps: u32,
    pub min_baseline_bps: u32,
    pub retainage_bps: u32,
    pub followup_delay_secs: u64,
    pub max_regrowth_bps: u32,
    pub baseline_deadline: u64,
    pub completion_deadline: u64,
    pub followup_deadline: u64,
    pub challenge_window_secs: u64,

    pub state: JobState,
    pub baseline_obs_id: Option<u64>,
    pub completion_obs_id: Option<u64>,
    pub followup_obs_id: Option<u64>,

    pub baseline_cover_bps: Option<u32>,
    pub completion_cover_bps: Option<u32>,
    pub followup_cover_bps: Option<u32>,

    pub baseline_image_hash: Option<BytesN<32>>,
    pub completion_image_hash: Option<BytesN<32>>,

    pub completion_recorded_at: Option<u64>,
    pub retained_amount: i128,
    pub paid_to_worker: i128,
    pub refunded_to_farmer: i128,

    pub dispute_timestamp: Option<u64>,
    pub dispute_outcome: Option<DisputeOutcome>,
}
