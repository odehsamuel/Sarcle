import React, { useState } from 'react';

export const CreateJob: React.FC = () => {
  const [farmer, setFarmer] = useState('G_FARMER_TESTNET');
  const [worker, setWorker] = useState('G_WORKER_TESTNET');
  const [arbiter, setArbiter] = useState('G_ARBITER_TESTNET');
  const [amount, setAmount] = useState('500');
  const [deviceId, setDeviceId] = useState('7e33a71be43d3f3925e08b7e0d9861547812ae4b66393c9a86022efd2087a3a3');
  const [thresholdBps, setThresholdBps] = useState('7500'); // 75%
  const [minBaselineBps, setMinBaselineBps] = useState('4000'); // 40%
  const [retainageBps, setRetainageBps] = useState('2000'); // 20%
  const [maxRegrowthBps, setMaxRegrowthBps] = useState('500'); // 5%
  const [roiHash, setRoiHash] = useState('');
  const [roiStatus, setRoiStatus] = useState<string | null>(null);

  const handleRoiUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (event) => {
      try {
        const text = event.target?.result as string;
        const parsed = JSON.parse(text);
        if (!parsed.points || !Array.isArray(parsed.points)) {
          setRoiStatus('Error: ROI must contain points array');
          return;
        }

        // Canonical formatting
        const canonicalPoints = parsed.points.map((p: any) => ({
          x: Number(p.x).toFixed(4),
          y: Number(p.y).toFixed(4),
        }));

        const canonicalJson = JSON.stringify({
          name: parsed.name || 'roi_polygon',
          points: canonicalPoints,
          version: 1,
        });

        // Compute SHA-256 using WebCrypto
        const encoder = new TextEncoder();
        const data = encoder.encode(canonicalJson);
        const hashBuf = await crypto.subtle.digest('SHA-256', data);
        const hashHex = Array.from(new Uint8Array(hashBuf))
          .map((b) => b.toString(16).padStart(2, '0'))
          .join('');

        setRoiHash(hashHex);
        setRoiStatus(`Canonical ROI SHA-256: ${hashHex} (${parsed.points.length} points)`);
      } catch (err: any) {
        setRoiStatus(`Error parsing JSON: ${err.message}`);
      }
    };
    reader.readAsText(file);
  };

  const handleCreateJob = (e: React.FormEvent) => {
    e.preventDefault();
    alert(`Job deployment ready! Parameters:\nAmount: ${amount} XLM\nROI Hash: ${roiHash || '084e1a3f688169af...'}\nThreshold: ${thresholdBps} bps\nRetainage: ${retainageBps} bps`);
  };

  return (
    <div style={{ maxWidth: '800px', margin: '2rem auto', padding: '0 1rem' }}>
      <div style={{
        padding: '1rem',
        backgroundColor: '#eff6ff',
        border: '1px solid #bfdbfe',
        borderRadius: '6px',
        marginBottom: '1.5rem',
      }}>
        <h4 style={{ margin: '0 0 0.5rem 0', color: '#1e40af' }}>Scope of Claim Notice</h4>
        <p style={{ margin: 0, fontSize: '0.9rem', color: '#1e3a8a' }}>
          This system measures changes in <strong>total green vegetation cover</strong> inside a fixed region.
          It does <strong>NOT</strong> distinguish weeds from crops. Jobs must target areas where all vegetation
          should be eradicated (fallow beds, paths, borders, drainage channels).
        </p>
      </div>

      <div style={{
        backgroundColor: '#ffffff',
        border: '1px solid #e2e8f0',
        borderRadius: '8px',
        padding: '2rem',
      }}>
        <h3 style={{ marginTop: 0 }}>Create Evidence-Gated Work Escrow</h3>

        <form onSubmit={handleCreateJob}>
          <div style={{ marginBottom: '1.25rem' }}>
            <label style={{ display: 'block', fontWeight: 500, marginBottom: '0.25rem' }}>Worker Stellar Address</label>
            <input
              type="text"
              value={worker}
              onChange={(e) => setWorker(e.target.value)}
              style={{ width: '100%', padding: '0.5rem', border: '1px solid #cbd5e1', borderRadius: '4px', fontFamily: 'monospace' }}
              required
            />
          </div>

          <div style={{ marginBottom: '1.25rem' }}>
            <label style={{ display: 'block', fontWeight: 500, marginBottom: '0.25rem' }}>Designated Arbiter Address</label>
            <input
              type="text"
              value={arbiter}
              onChange={(e) => setArbiter(e.target.value)}
              style={{ width: '100%', padding: '0.5rem', border: '1px solid #cbd5e1', borderRadius: '4px', fontFamily: 'monospace' }}
              required
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.25rem' }}>
            <div>
              <label style={{ display: 'block', fontWeight: 500, marginBottom: '0.25rem' }}>Escrow Amount (XLM)</label>
              <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                style={{ width: '100%', padding: '0.5rem', border: '1px solid #cbd5e1', borderRadius: '4px' }}
                required
              />
            </div>
            <div>
              <label style={{ display: 'block', fontWeight: 500, marginBottom: '0.25rem' }}>Registered Device Public Key</label>
              <input
                type="text"
                value={deviceId}
                onChange={(e) => setDeviceId(e.target.value)}
                style={{ width: '100%', padding: '0.5rem', border: '1px solid #cbd5e1', borderRadius: '4px', fontFamily: 'monospace' }}
                required
              />
            </div>
          </div>

          <div style={{ marginBottom: '1.25rem' }}>
            <label style={{ display: 'block', fontWeight: 500, marginBottom: '0.25rem' }}>Upload Canonical ROI Polygon (.json)</label>
            <input
              type="file"
              accept=".json"
              onChange={handleRoiUpload}
              style={{ padding: '0.5rem 0' }}
            />
            {roiStatus && (
              <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.85rem', color: roiHash ? '#15803d' : '#b91c1c', fontFamily: 'monospace' }}>
                {roiStatus}
              </p>
            )}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
            <div>
              <label style={{ display: 'block', fontWeight: 500, marginBottom: '0.25rem', fontSize: '0.85rem' }}>Threshold (bps)</label>
              <input
                type="number"
                value={thresholdBps}
                onChange={(e) => setThresholdBps(e.target.value)}
                style={{ width: '100%', padding: '0.4rem', border: '1px solid #cbd5e1', borderRadius: '4px' }}
              />
              <span style={{ fontSize: '0.75rem', color: '#64748b' }}>e.g. 7500 = 75% reduction</span>
            </div>
            <div>
              <label style={{ display: 'block', fontWeight: 500, marginBottom: '0.25rem', fontSize: '0.85rem' }}>Retainage (bps)</label>
              <input
                type="number"
                value={retainageBps}
                onChange={(e) => setRetainageBps(e.target.value)}
                style={{ width: '100%', padding: '0.4rem', border: '1px solid #cbd5e1', borderRadius: '4px' }}
              />
              <span style={{ fontSize: '0.75rem', color: '#64748b' }}>e.g. 2000 = 20% held</span>
            </div>
            <div>
              <label style={{ display: 'block', fontWeight: 500, marginBottom: '0.25rem', fontSize: '0.85rem' }}>Max Regrowth (bps)</label>
              <input
                type="number"
                value={maxRegrowthBps}
                onChange={(e) => setMaxRegrowthBps(e.target.value)}
                style={{ width: '100%', padding: '0.4rem', border: '1px solid #cbd5e1', borderRadius: '4px' }}
              />
              <span style={{ fontSize: '0.75rem', color: '#64748b' }}>e.g. 500 = 5% max growth</span>
            </div>
          </div>

          <button
            type="submit"
            style={{
              padding: '0.75rem 1.5rem',
              backgroundColor: '#15803d',
              color: '#ffffff',
              border: 'none',
              borderRadius: '6px',
              fontWeight: 600,
              cursor: 'pointer',
              width: '100%',
            }}
          >
            Deposit Funds & Initialize Job
          </button>
        </form>
      </div>
    </div>
  );
};
