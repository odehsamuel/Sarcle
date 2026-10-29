import React, { useState } from 'react';
import { Navigation } from './components/Navigation';
import { Footer } from './components/Footer';
import { CreateJob } from './pages/CreateJob';
import { JobDetail } from './pages/JobDetail';
import { ArbiterConsole } from './pages/ArbiterConsole';
import { RegistryView } from './pages/RegistryView';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState('create');
  const [walletAddress, setWalletAddress] = useState<string | null>(null);

  const handleConnectWallet = async () => {
    // In production, uses @creit-tech/stellar-wallets-kit or freighter-api
    const mockFreighterKey = 'GBRA4DOKRWYBXVOXY2ELGJKFRX6VGGPRYUWHQ7PMXXJNDZFMKD';
    setWalletAddress(mockFreighterKey);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Navigation
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        walletAddress={walletAddress}
        onConnectWallet={handleConnectWallet}
      />

      <main style={{ flex: 1 }}>
        {activeTab === 'create' && <CreateJob />}
        {activeTab === 'jobs' && <JobDetail />}
        {activeTab === 'arbiter' && <ArbiterConsole />}
        {activeTab === 'registry' && <RegistryView />}
      </main>

      <Footer />
    </div>
  );
};
