use soroban_sdk::contracterror;

#[contracterror]
#[derive(Copy, Clone, Debug, Eq, PartialEq, PartialOrd, Ord)]
#[repr(u32)]
pub enum EscrowError {
    AlreadyInitialized = 1,
    NotInitialized = 2,
    Unauthorized = 3,
    InvalidAmount = 4,
    InvalidDeadlines = 5,
    InvalidBasisPoints = 6,
    JobNotFound = 7,
    InvalidJobState = 8,
    RegistryCallFailed = 9,
    ObservationJobMismatch = 10,
    ObservationKindMismatch = 11,
    ObservationDeviceMismatch = 12,
    ObservationRoiMismatch = 13,
    ObservationMetricMismatch = 14,
    ObservationNotAccepted = 15,
    BaselineTooLow = 16,
    DuplicateImage = 17,
    DeadlineExceeded = 18,
    ChallengeWindowActive = 19,
    ChallengeWindowExpired = 20,
    FollowupDelayNotMet = 21,
    DisputeActive = 22,
    NoDisputeActive = 23,
    ArbiterTimeoutNotReached = 24,
    MathOverflow = 25,
}
