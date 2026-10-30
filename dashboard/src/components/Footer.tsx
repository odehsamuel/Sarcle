import React from 'react';

export const Footer: React.FC = () => {
  return (
    <footer style={{
      marginTop: '3rem',
      padding: '1.5rem',
      borderTop: '1px solid #e2e8f0',
      textAlign: 'center',
      backgroundColor: '#ffffff',
      color: '#64748b',
      fontSize: '0.875rem'
    }}>
      <p style={{ margin: 0, fontWeight: 500 }}>
        ⚠️ <strong>Testnet prototype. Not a production payment system.</strong>
      </p>
      <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.75rem' }}>
        Sarcle protocol on Stellar/Soroban. Classical computer vision only. No mainnet release.
      </p>
    </footer>
  );
};
