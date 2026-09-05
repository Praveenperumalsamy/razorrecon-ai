import { createContext, useContext, useState, type ReactNode } from 'react';

export type TabKey =
  | 'dashboard'
  | 'upload'
  | 'reconciliation'
  | 'exceptions'
  | 'audit'
  | 'evaluation';

interface NavContextValue {
  tab: TabKey;
  goToTab: (tab: TabKey) => void;
  selectedTxId: string | null;
  openTransaction: (id: string) => void;
  closeTransaction: () => void;
}

const NavContext = createContext<NavContextValue | undefined>(undefined);

export function NavProvider({ children }: { children: ReactNode }) {
  const [tab, setTab] = useState<TabKey>('dashboard');
  const [selectedTxId, setSelectedTxId] = useState<string | null>(null);

  const goToTab = (next: TabKey) => {
    setSelectedTxId(null);
    setTab(next);
  };

  const openTransaction = (id: string) => setSelectedTxId(id);
  const closeTransaction = () => setSelectedTxId(null);

  return (
    <NavContext.Provider value={{ tab, goToTab, selectedTxId, openTransaction, closeTransaction }}>
      {children}
    </NavContext.Provider>
  );
}

export function useAppNav(): NavContextValue {
  const ctx = useContext(NavContext);
  if (!ctx) throw new Error('useAppNav must be used within a NavProvider');
  return ctx;
}
