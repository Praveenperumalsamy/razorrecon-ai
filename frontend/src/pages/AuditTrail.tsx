import React, { useEffect, useState } from 'react';
import { getAuditTrail } from '../services/api';
import { AuditEntry } from '../types';
import { useAppNav } from '../context/NavContext';
import { Search, Bot, User, CheckCircle, AlertTriangle, XCircle, SearchIcon } from 'lucide-react';

export const AuditTrail: React.FC = () => {
  const { openTransaction } = useAppNav();
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    const fetchAudit = async () => {
      try {
        setLoading(true);
const res = await getAuditTrail();
        setEntries(res.data);
      } catch (error) {
        console.error('Failed to fetch audit trail', error);
      } finally {
        setLoading(false);
      }
    };
    fetchAudit();
  }, []);

  const filteredEntries = entries.filter(entry => 
    entry.transaction_id.toLowerCase().includes(search.toLowerCase()) ||
    entry.action.toLowerCase().includes(search.toLowerCase())
  );

  const getActionIcon = (action: string) => {
    if (action.includes('approve') || action.includes('reconcile')) return <CheckCircle size={16} className="text-emerald-400" />;
    if (action.includes('reject')) return <XCircle size={16} className="text-rose-400" />;
    return <AlertTriangle size={16} className="text-amber-400" />;
  };

  if (loading) {
    return <div className="space-y-4">
      {[1,2,3,4,5].map(i => <div key={i} className="animate-pulse bg-navy-800/50 h-24 rounded-xl border border-white/5"></div>)}
    </div>;
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="bg-navy-800/50 backdrop-blur-xl border border-white/10 rounded-2xl p-6">
        <div className="relative max-w-md">
          <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <input
            type="text"
            placeholder="Search by Transaction ID or Action..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-navy-900/50 border border-white/10 rounded-xl py-2 pl-10 pr-4 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
          />
        </div>
      </div>

      <div className="bg-navy-800/50 backdrop-blur-xl border border-white/10 rounded-2xl p-6">
        <div className="space-y-8 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-white/10 before:to-transparent">
          {filteredEntries.map((entry, idx) => (
            <div key={idx} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
              <div className={`flex items-center justify-center w-10 h-10 rounded-full border-4 border-navy-900 shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 ${
                entry.agent === 'system' ? 'bg-blue-500/20 text-blue-400' : 'bg-emerald-500/20 text-emerald-400'
              }`}>
                {entry.agent === 'system' ? <Bot size={18} /> : <User size={18} />}
              </div>
              
              <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] bg-navy-900/50 hover:bg-navy-800/80 transition-colors p-5 rounded-2xl border border-white/5">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    {getActionIcon(entry.action)}
                    <span className="font-semibold text-white text-sm capitalize">{entry.action.replace(/_/g, ' ')}</span>
                  </div>
                  <time className="text-xs text-slate-500 font-mono">{new Date(entry.timestamp).toLocaleString()}</time>
                </div>
                
                <p className="text-sm text-slate-300 mb-3">{entry.reason}</p>
                
                <div className="flex flex-wrap items-center gap-3 text-xs">
                  <button
                    onClick={() => openTransaction(entry.transaction_id)}
                    className="text-blue-400 hover:text-blue-300 hover:underline flex items-center gap-1 font-mono"
                  >
                    TX: {entry.transaction_id.substring(0, 8)}...
                  </button>
                  <span className="text-slate-600">•</span>
                  <span className="text-slate-400 flex items-center gap-1">
                    Agent: <span className="text-white capitalize">{entry.agent}</span>
                  </span>
                  {entry.confidence > 0 && (
                    <>
                      <span className="text-slate-600">•</span>
                      <span className="text-slate-400">
                        Conf: <span className="text-white">{Math.round(entry.confidence * 100)}%</span>
                      </span>
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}

          {filteredEntries.length === 0 && (
            <div className="text-center text-slate-500 py-12 relative z-10 bg-navy-800 rounded-xl">
              No audit entries found matching your search.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
