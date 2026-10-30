import React from 'react';

interface NavigationProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  walletAddress: string | null;
  onConnectWallet: () => void;
}

export const Navigation: React.FC<NavigationProps> = ({
  activeTab,
  setActiveTab,
  walletAddress,
  onConnectWallet,
}) => {
  const tabs = [
    { id: 'create', label: 'Create Job' },
    { id: 'jobs', label: 'Job Detail' },
    { id: 'arbiter', label: 'Arbiter Console' },
    { id: 'registry', label: 'Evidence Registry' },
  ];

  return (
    <header style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '1rem 2rem',
      backgroundColor: '#ffffff',
      borderBottom: '1px solid #e2e8f0',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <svg width="30" height="30" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="50" cy="50" r="44" fill="#15803d" stroke="#166534" strokeWidth="6"/>
            <path d="M32 66 C36 44, 56 34, 72 30 C66 52, 50 66, 32 66 Z" fill="#ffffff"/>
            <circle cx="50" cy="50" r="9" fill="#86efac"/>
          </svg>
          <h2 style={{ margin: 0, color: '#15803d', fontSize: '1.4rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
            Sarcle
          </h2>
        </div>
        <nav style={{ display: 'flex', gap: '1rem' }}>
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                background: 'none',
                border: 'none',
                padding: '0.5rem 0.75rem',
                fontSize: '0.95rem',
                fontWeight: activeTab === tab.id ? 600 : 400,
                color: activeTab === tab.id ? '#15803d' : '#64748b',
                borderBottom: activeTab === tab.id ? '2px solid #15803d' : '2px solid transparent',
                cursor: 'pointer',
              }}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      <div>
        {walletAddress ? (
          <span style={{
            fontSize: '0.85rem',
            padding: '0.4rem 0.8rem',
            backgroundColor: '#f1f5f9',
            borderRadius: '4px',
            fontFamily: 'monospace',
          }}>
            {walletAddress.slice(0, 6)}...{walletAddress.slice(-4)}
          </span>
        ) : (
          <button
            onClick={onConnectWallet}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#15803d',
              color: '#ffffff',
              border: 'none',
              borderRadius: '4px',
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            Connect Freighter
          </button>
        )}
      </div>
    </header>
  );
};
