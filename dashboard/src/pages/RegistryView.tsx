import React from 'react';

export const RegistryView: React.FC = () => {
  const devices = [
    {
      deviceId: '7e33a71be43d3f3925e08b7e0d9861547812ae4b66393c9a86022efd2087a3a3',
      registeredAt: '2026-10-29',
      status: 'Active',
      lastCounter: 42,
    },
  ];

  const attesters = [
    { address: 'G_ATTESTER_A_PYTHON', label: 'Attester A (Python / Flask)', status: 'Active' },
    { address: 'G_ATTESTER_B_RUST', label: 'Attester B (Rust / CIELAB)', status: 'Active' },
  ];

  const analyzers = [
    {
      hash: '0212ff0c95...',
      metricId: 1,
      metricName: 'green_cover_exg',
      familyId: 1,
      familyName: 'OpenCV ExG (Python)',
      status: 'Allowlisted',
    },
    {
      hash: 'c19c2535ad...',
      metricId: 1,
      metricName: 'green_cover_exg',
      familyId: 2,
      familyName: 'CIELAB a* Fixed Point (Rust)',
      status: 'Allowlisted',
    },
  ];

  return (
    <div style={{ maxWidth: '900px', margin: '2rem auto', padding: '0 1rem' }}>
      <div style={{
        backgroundColor: '#ffffff',
        border: '1px solid #e2e8f0',
        borderRadius: '8px',
        padding: '1.5rem',
        marginBottom: '1.5rem',
      }}>
        <h3 style={{ margin: '0 0 0.5rem 0' }}>Evidence Registry Status</h3>
        <p style={{ margin: 0, fontSize: '0.9rem', color: '#64748b' }}>
          On-chain trust anchors: active capture devices, authorized attesters, and allowlisted deterministic analyzers.
        </p>
      </div>

      {/* Authorized Edge Devices */}
      <div style={{ backgroundColor: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1.5rem', marginBottom: '1.5rem' }}>
        <h4 style={{ margin: '0 0 1rem 0' }}>Registered Edge Capture Devices</h4>
        {devices.map((d) => (
          <div key={d.deviceId} style={{ padding: '0.75rem', backgroundColor: '#f8fafc', borderRadius: '4px', border: '1px solid #f1f5f9' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
              <code style={{ fontSize: '0.85rem' }}>{d.deviceId}</code>
              <span style={{ fontSize: '0.75rem', color: '#15803d', fontWeight: 600 }}>{d.status}</span>
            </div>
            <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
              Persistent Counter: {d.lastCounter} • Registered: {d.registeredAt}
            </div>
          </div>
        ))}
      </div>

      {/* Authorized Attesters */}
      <div style={{ backgroundColor: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1.5rem', marginBottom: '1.5rem' }}>
        <h4 style={{ margin: '0 0 1rem 0' }}>Authorized Attestation Operators</h4>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          {attesters.map((a) => (
            <div key={a.address} style={{ padding: '0.75rem', backgroundColor: '#f8fafc', borderRadius: '4px', border: '1px solid #f1f5f9' }}>
              <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{a.label}</div>
              <code style={{ fontSize: '0.8rem', color: '#64748b' }}>{a.address}</code>
              <div style={{ fontSize: '0.75rem', color: '#15803d', marginTop: '0.25rem' }}>Status: {a.status}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Allowlisted Analyzers */}
      <div style={{ backgroundColor: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1.5rem' }}>
        <h4 style={{ margin: '0 0 1rem 0' }}>Allowlisted Deterministic Analyzers</h4>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #e2e8f0', textAlign: 'left', color: '#64748b' }}>
              <th style={{ padding: '0.5rem 0' }}>Metric</th>
              <th>Family</th>
              <th>Analyzer Hash</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {analyzers.map((an) => (
              <tr key={an.hash} style={{ borderBottom: '1px solid #f1f5f9' }}>
                <td style={{ padding: '0.6rem 0' }}>{an.metricName} (ID {an.metricId})</td>
                <td>{an.familyName}</td>
                <td><code>{an.hash}</code></td>
                <td style={{ color: '#15803d', fontWeight: 500 }}>{an.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
