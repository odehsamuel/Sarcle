use soroban_sdk::contracterror;

#[contracterror]
#[derive(Copy, Clone, Debug, Eq, PartialEq, PartialOrd, Ord)]
#[repr(u32)]
pub enum RegistryError {
    AlreadyInitialized = 1,
    NotInitialized = 2,
    Unauthorized = 3,
    DeviceAlreadyRegistered = 4,
    DeviceNotFound = 5,
    DeviceRevoked = 6,
    AttesterNotFound = 7,
    AttesterNotActive = 8,
    AnalyzerNotAllowed = 9,
    InvalidMetricValue = 10,
    ChallengeNotFound = 11,
    ChallengeExpired = 12,
    ChallengeAlreadyUsed = 13,
    ChallengeMismatch = 14,
    TimestampOutOfRange = 15,
    CounterNotIncreasing = 16,
    InvalidSignature = 17,
    ObservationNotFound = 18,
    DuplicateAttesterAnalysis = 19,
    DuplicateFamilyAnalysis = 20,
    InvalidObservationKind = 21,
    ObservationAlreadyQuorum = 22,
    InvalidMessageLength = 23,
    ConfigError = 24,
}
