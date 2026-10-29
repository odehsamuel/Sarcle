import React, { useState } from 'react';

export const ArbiterConsole: React.FC = () => {
  const [activeDispute, setActiveDispute] = useState({
    jobId: 104,
    farmer: 'G_FARMER_BOB',
    worker: 'G_WORKER_ALICE',
    amount: 1000,
    divergenceReason: 'Analyzers Diverged (Divergence = 680 bps > 500 bps limit)',
    baselineImage: 'attester-a/storage/images/sample_base.jpg',
    completionImage: 'attester-a/storage/images/sample_comp.jpg',
    disputeDate: '2026-10-29 22:15 UTC',
  });

  const handleResolve = (outcome: 'FarmerWins' | 'WorkerWins' | 'Split') => {
    alert(`Arbiter Decision executed on-chain via resolve(job_id=${activeDispute.jobId}, outcome=${outcome}).\nFunds disbursed.`);
  };

  return (
    <div style={{ maxWidth: '900px', margin: '2rem auto', padding: '0 1rem' }}>
      <div style={{
        backgroundColor: '#ffffff',
        border: '1px solid #e2e8f0',
        borderRadius: '8px',
        padding: '1.5rem',
        marginBottom: '1.5rem',
      }}>
        <h3 style={{ margin: '0 0 0.5rem 0' }}>Arbiter Adjudication Console</h3>
        <p style={{ margin: 0, fontSize: '0.9rem', color: '#64748b' }}>
          Review contested vegetation clearing jobs and resolve disputes based on raw sensory evidence.
        </p>
      </div>

      <div style={{
        backgroundColor: '#ffffff',
        border: '1px solid #e2e8f0',
        borderRadius: '8px',
        padding: '1.5rem',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <div>
            <strong>Dispute on Job #{activeDispute.jobId}</strong>
            <div style={{ fontSize: '0.85rem', color: '#64748b' }}>Escrowed Amount: {activeDispute.amount} XLM</div>
          </div>
          <span style={{
            padding: '0.3rem 0.6rem',
            backgroundColor: '#fee2e2',
            color: '#b91c1c',
            borderRadius: '4px',
            fontSize: '0.8rem',
            fontWeight: 600,
          }}>
            Status: Disputed
          </span>
        </div>

        <div style={{
          padding: '0.75rem',
          backgroundColor: '#fef2f2',
          border: '1px solid #fecaca',
          borderRadius: '4px',
          marginBottom: '1.5rem',
          fontSize: '0.9rem',
          color: '#991b1b',
        }}>
          Reason: {activeDispute.divergenceReason}
        </div>

        {/* Side-by-side Evidence Placeholders */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
          <div style={{ textAlign: 'center', padding: '1rem', backgroundColor: '#f8fafc', borderRadius: '4px' }}>
            <div style={{ fontWeight: 500, marginBottom: '0.5rem' }}>Baseline Evidence Frame</div>
            <div style={{ height: '160px', backgroundColor: '#cbd5e1', borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#475569' }}>
              [Captured Baseline Frame]
            </div>
            <span style={{ fontSize: '0.8rem', color: '#64748b' }}>Initial Cover: ~62%</span>
          </div>

          <div style={{ textAlign: 'center', padding: '1rem', backgroundColor: '#f8fafc', borderRadius: '4px' }}>
            <div style={{ fontWeight: 500, marginBottom: '0.5rem' }}>Completion Evidence Frame</div>
            <div style={{ height: '160px', backgroundColor: '#cbd5e1', borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#475569' }}>
              [Captured Completion Frame]
            </div>
            <span style={{ fontSize: '0.8rem', color: '#64748b' }}>Reported Cover: ~12% vs 5%</span>
          </div>
        </div>

        {/* Adjudication Actions */}
        <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: '1.25rem' }}>
          <h4 style={{ margin: '0 0 1rem 0' }}>Arbiter Judgment</h4>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <button
              onClick={() => handleResolve('WorkerWins')}
              style={{
                flex: 1,
                padding: '0.6rem 1rem',
                backgroundColor: '#15803d',
                color: '#ffffff',
                border: 'none',
                borderRadius: '4px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Award 100% to Worker
            </button>
            <button
              onClick={() => handleResolve('Split')}
              style={{
                flex: 1,
                padding: '0.6rem 1rem',
                backgroundColor: '#0284c7',
                color: '#ffffff',
                border: 'none',
                borderRadius: '4px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Split 50% / 50%
            </button>
            <button
              onClick={() => handleResolve('FarmerWins')}
              style={{
                flex: 1,
                padding: '0.6rem 1rem',
                backgroundColor: '#dc2626',
                color: '#ffffff',
                border: 'none',
                borderRadius: '4px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Refund 100% to Farmer
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
