import React from 'react';
import {
  LayoutDashboard,
  UploadCloud,
  ArrowLeftRight,
  AlertTriangle,
  History,
  BarChart3,
  Zap,
  LogOut,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useAppNav, type TabKey } from '../context/NavContext';
import { Dashboard } from '../pages/Dashboard';
import { Upload } from '../pages/Upload';
import { Reconciliation } from '../pages/Reconciliation';
import { Exceptions } from '../pages/Exceptions';
import { AuditTrail } from '../pages/AuditTrail';
import { Evaluation } from '../pages/Evaluation';
import { TransactionDetail } from '../pages/TransactionDetail';
import { AIChatWidget } from './AIChatWidget';

const TAB_COMPONENTS: Record<TabKey, React.ComponentType> = {
  dashboard: Dashboard,
  upload: Upload,
  reconciliation: Reconciliation,
  exceptions: Exceptions,
  audit: AuditTrail,
  evaluation: Evaluation,
};

export const Layout: React.FC = () => {
  const { user, logout, hasMinRole } = useAuth();
  const { tab, goToTab, selectedTxId, closeTransaction } = useAppNav();

  type NavItem = { key: TabKey; label: string; icon: React.ReactNode; minRole?: 'reviewer' };
  const allNavItems: NavItem[] = [
    { key: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={20} /> },
    { key: 'upload', label: 'Upload Data', icon: <UploadCloud size={20} />, minRole: 'reviewer' },
    { key: 'reconciliation', label: 'Reconciliation', icon: <ArrowLeftRight size={20} />, minRole: 'reviewer' },
    { key: 'exceptions', label: 'Exceptions', icon: <AlertTriangle size={20} /> },
    { key: 'audit', label: 'Audit Trail', icon: <History size={20} /> },
    { key: 'evaluation', label: 'Evaluation', icon: <BarChart3 size={20} /> },
  ];
  const navItems = allNavItems.filter((item) => !item.minRole || hasMinRole(item.minRole));

  const currentLabel = navItems.find((item) => item.key === tab)?.label || 'Dashboard';
  const ActiveTab = TAB_COMPONENTS[tab];

  return (
    <div className="flex h-screen bg-navy-900 text-slate-200 overflow-hidden font-sans">
      {/* Sidebar */}
      <aside className="w-64 bg-navy-800 border-r border-white/5 flex flex-col transition-all duration-300 flex-shrink-0">
        <div className="p-6 flex items-center gap-3 border-b border-white/5">
          <div className="bg-blue-500/20 text-blue-400 p-2 rounded-xl">
            <Zap size={24} className="fill-current" />
          </div>
          <div>
            <h1 className="font-bold text-lg text-white tracking-tight">RazorRecon AI</h1>
            <p className="text-xs text-blue-400 font-medium">AI Finance Controller</p>
          </div>
        </div>

        <nav className="flex-1 py-6 px-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => (
            <button
              key={item.key}
              onClick={() => goToTab(item.key)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 font-medium text-sm text-left ${
                tab === item.key && !selectedTxId
                  ? 'bg-blue-500/10 text-blue-400'
                  : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
              }`}
            >
              {item.icon}
              {item.label}
            </button>
          ))}
        </nav>

        <div className="p-4 border-t border-white/5">
          <div className="flex items-center gap-3 px-2 py-2">
            <div className="w-8 h-8 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center text-xs font-semibold flex-shrink-0">
              {(user?.full_name || user?.email || '?').charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium text-slate-200 truncate">{user?.full_name || user?.email}</p>
              <p className="text-[10px] uppercase tracking-wide text-slate-500">{user?.role}</p>
            </div>
            <button
              onClick={logout}
              title="Sign out"
              className="text-slate-500 hover:text-red-400 transition p-1"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
        <div className="px-6 pb-4 text-xs text-slate-500 font-medium">
          Version 2.0.0
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden relative">
        {/* Subtle background glow */}
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-blue-500/10 blur-[120px] rounded-full pointer-events-none" />

        <header className="h-20 flex items-center px-8 border-b border-white/5 z-10 backdrop-blur-sm bg-navy-900/50">
          <h2 className="text-xl font-semibold text-white">
            {selectedTxId ? 'Transaction Detail' : currentLabel}
          </h2>
        </header>

        <div className="flex-1 overflow-y-auto p-8 z-10">
          {selectedTxId ? (
            <TransactionDetail id={selectedTxId} onBack={closeTransaction} />
          ) : (
            <ActiveTab />
          )}
        </div>
      </main>

      {/* AI assistant — always available, bottom right */}
      <AIChatWidget />
    </div>
  );
};
