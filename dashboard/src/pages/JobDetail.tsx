import React, { useState } from 'react';

export const JobDetail: React.FC = () => {
  const [jobId, setJobId] = useState('1');
  const [jobState, setJobState] = useState<'Funded' | 'BaselineRecorded' | 'CompletionRecorded' | 'CompletionPaid' | 'FollowupRecorded' | 'Settled' | 'Disputed'>('CompletionRecorded');
  const [challengeWindowSeconds, setChallengeWindowSeconds] = useState(1420); // 23 mins left
  const [disputeTriggered, setDisputeTriggered] = useState(false);

  // Sample data representing dual-analyzer observations
  const observations = [
    {
      id: 101,
      kind: 'Baseline',
      timestamp: '2026-10-29 21:00 UTC',
      analyzerA: { name: 'ExG (Python)', coverBps: 6200 },
      analyzerB: { name: 'CIELAB a* (Rust)', coverBps: 6280 },
      divergenceBps: 80,
      status: 'Accepted',
      acceptedBps: 6240,
    },
    {
      id: 102,
      kind: 'Completion',
      timestamp: '2026-10-29 22:30 UTC',
      analyzerA: { name: 'ExG (Python)', coverBps: 920 },
      analyzerB: { name: 'CIELAB a* (Rust)', coverBps: 880 },
      divergenceBps: 40,
      status: 'Accepted',
      acceptedBps: 900,
    },
  ];

  const handleFinalize = () => {
    alert('Calling work_escrow::finalize_completion(job_id=1)...\nPrimary payout (80%) released to worker, 20% retainage locked.');
    setJobState('CompletionPaid');
  };

  const handleDispute = () => {
    alert('Filing dispute on Job 1...\nJob moved to Disputed state. Escrow funds locked until Arbiter adjudication.');
    setJobState('Disputed');
    setDisputeTriggered(true);
  };

  return (
    <div style={{ maxWidth: '900px', margin: '2rem auto', padding: '0 1rem' }}>
      {/* State Machine Timeline */}
      <div style={{
        backgroundColor: '#ffffff',
        border: '1px solid #e2e8f0',
        borderRadius: '8px',
        padding: '1.5rem',
        marginBottom: '1.5rem',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 style={{ margin: 0 }}>Job #{jobId} Detail</h3>
            <span style={{ fontSize: '0.85rem', color: '#64748b' }}>Reference ID: 1001 • Escrow: 1,000 XLM</span>
          </div>
          <span style={{
            padding: '0.4rem 0.8rem',
            borderRadius: '20px',
            fontSize: '0.85rem',
            fontWeight: 600,
            backgroundColor: jobState === 'Disputed' ? '#fee2e2' : '#dcfce7',
            color: jobState === 'Disputed' ? '#b91c1c' : '#15803d',
          }}>
            {jobState}
          </span>
        </div>

        {/* Timeline visualization */}
        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1.5rem' }}>
          {['Funded', 'BaselineRecorded', 'CompletionRecorded', 'CompletionPaid', 'Settled'].map((s, idx) => {
            const isCompleted = ['CompletionRecorded', 'CompletionPaid', 'Settled'].indexOf(jobState) >= ['CompletionRecorded', 'CompletionPaid', 'Settled'].indexOf(s);
            return (
              <div key={s} style={{ flex: 1, textAlign: 'center' }}>
                <div style={{
                  height: '4px',
                  backgroundColor: isCompleted ? '#15803d' : '#e2e8f0',
                  marginBottom: '0.5rem',
                }} />
                <span style={{ fontSize: '0.75rem', color: isCompleted ? '#15803d' : '#94a3b8', fontWeight: isCompleted ? 600 : 400 }}>
                  {s}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Challenge Window & Retainage Banner */}
      {jobState === 'CompletionRecorded' && (
        <div style={{
          padding: '1.25rem',
          backgroundColor: '#fef3c7',
          border: '1px solid #fde68a',
          borderRadius: '8px',
          marginBottom: '1.5rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <div>
            <h4 style={{ margin: '0 0 0.25rem 0', color: '#92400e' }}>Challenge Window Active</h4>
            <p style={{ margin: 0, fontSize: '0.9rem', color: '#b45309' }}>
              Countdown: <strong>{Math.floor(challengeWindowSeconds / 60)}m {challengeWindowSeconds % 60}s</strong> remaining before completion can be finalized.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <button
              onClick={handleFinalize}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: '#15803d',
                color: '#ffffff',
                border: 'none',
                borderRadius: '4px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Finalize Completion
            </button>
            <button
              onClick={handleDispute}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: '#ef4444',
                color: '#ffffff',
                border: 'none',
                borderRadius: '4px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Raise Dispute
            </button>
          </div>
        </div>
      )}

      {/* Observations & Dual Analysis Cards */}
      <h3 style={{ marginBottom: '1rem' }}>Attached Evidence Observations</h3>
      {observations.map((obs) => (
        <div key={obs.id} style={{
          backgroundColor: '#ffffff',
          border: '1px solid #e2e8f0',
          borderRadius: '8px',
          padding: '1.25rem',
          marginBottom: '1rem',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
            <div>
              <strong>Observation #{obs.id} ({obs.kind})</strong>
              <div style={{ fontSize: '0.8rem', color: '#64748b' }}>{obs.timestamp}</div>
            </div>
            <span style={{
              fontSize: '0.85rem',
              fontWeight: 600,
              color: obs.divergenceBps <= 500 ? '#15803d' : '#b91c1c',
            }}>
              Quorum: {obs.status} (Mean: {obs.acceptedBps} bps / {(obs.acceptedBps / 100).toFixed(2)}%)
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div style={{ padding: '0.75rem', backgroundColor: '#f8fafc', borderRadius: '4px', border: '1px solid #f1f5f9' }}>
              <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Attester A • {obs.analyzerA.name}</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 600, marginTop: '0.25rem' }}>
                {obs.analyzerA.coverBps} bps ({(obs.analyzerA.coverBps / 100).toFixed(2)}%)
              </div>
            </div>

            <div style={{ padding: '0.75rem', backgroundColor: '#f8fafc', borderRadius: '4px', border: '1px solid #f1f5f9' }}>
              <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Attester B • {obs.analyzerB.name}</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 600, marginTop: '0.25rem' }}>
                {obs.analyzerB.coverBps} bps ({(obs.analyzerB.coverBps / 100).toFixed(2)}%)
              </div>
            </div>
          </div>

          <div style={{ marginTop: '0.75rem', fontSize: '0.8rem', color: '#64748b', display: 'flex', justifyContent: 'space-between' }}>
            <span>Analyzer Divergence: <strong>{obs.divergenceBps} bps</strong> (Threshold: 500 bps)</span>
            <span style={{ color: obs.divergenceBps <= 500 ? '#15803d' : '#b91c1c' }}>
              {obs.divergenceBps <= 500 ? '✓ Within Protocol Tolerance' : '⚠️ Exceeds Tolerance'}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
};
