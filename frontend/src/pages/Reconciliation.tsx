import React, { useEffect, useState } from 'react';
import { getTransactions } from '../services/api';
import { Transaction } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { ConfidenceBar } from '../components/ConfidenceBar';
import { useAppNav } from '../context/NavContext';
import { Search, Filter, ChevronRight } from 'lucide-react';

export const Reconciliation: React.FC = () => {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');
  const { openTransaction } = useAppNav();

  useEffect(() => {
    const fetchTx = async () => {
      try {
        setLoading(true);
        const res = await getTransactions();
        setTransactions(res.data);
      } catch (error) {
        console.error('Failed to fetch transactions', error);
      } finally {
        setLoading(false);
      }
    };
    fetchTx();
  }, []);

  const filteredTransactions = transactions.filter(tx => {
    const matchesSearch = tx.payment_id.toLowerCase().includes(search.toLowerCase());
    const matchesFilter = filter === 'all' || tx.status === filter;
    return matchesSearch && matchesFilter;
  });

  const formatCurrency = (amount: number, currency: string) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(amount);
  };

  if (loading) {
    return <div className="animate-pulse bg-navy-800/50 h-96 rounded-2xl border border-white/5"></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <input
            type="text"
            placeholder="Search by Payment ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-navy-800/50 border border-white/10 rounded-xl py-2 pl-10 pr-4 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
          />
        </div>
        <div className="flex items-center gap-3">
          <Filter className="text-slate-400" size={18} />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="bg-navy-800/50 border border-white/10 rounded-xl py-2 px-4 text-white focus:outline-none focus:border-blue-500 transition-colors appearance-none"
          >
            <option value="all">All Statuses</option>
            <option value="auto_reconciled">Auto-Reconciled</option>
            <option value="ai_review">AI Review</option>
            <option value="human_review">Human Review</option>
            <option value="exception">Exception</option>
          </select>
        </div>
      </div>

      <div className="bg-navy-800/50 backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-white/5 bg-navy-900/50">
                <th className="px-6 py-4 text-xs font-medium text-slate-400 uppercase tracking-wider">Payment ID</th>
                <th className="px-6 py-4 text-xs font-medium text-slate-400 uppercase tracking-wider">Bank</th>
                <th className="px-6 py-4 text-xs font-medium text-slate-400 uppercase tracking-wider">Ledger</th>
                <th className="px-6 py-4 text-xs font-medium text-slate-400 uppercase tracking-wider">Confidence</th>
                <th className="px-6 py-4 text-xs font-medium text-slate-400 uppercase tracking-wider">Status</th>
                <th className="px-6 py-4 text-xs font-medium text-slate-400 uppercase tracking-wider">Type</th>
                <th className="px-6 py-4"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {filteredTransactions.map((tx) => (
                <tr 
                  key={tx.id} 
                  onClick={() => openTransaction(tx.id)}
                  className="hover:bg-white/[0.02] transition-colors cursor-pointer group"
                >
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-white">{tx.payment_id}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">{formatCurrency(tx.bank_amount, tx.currency)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">{formatCurrency(tx.ledger_amount, tx.currency)}</td>
                  <td className="px-6 py-4 whitespace-nowrap w-48"><ConfidenceBar confidence={tx.confidence} /></td>
                  <td className="px-6 py-4 whitespace-nowrap"><StatusBadge status={tx.status} /></td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-400 capitalize">{tx.match_type.replace('_', ' ')}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <ChevronRight size={18} className="text-slate-500 group-hover:text-white transition-colors inline-block" />
                  </td>
                </tr>
              ))}
              {filteredTransactions.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center text-slate-500">
                    No transactions found matching your criteria.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
