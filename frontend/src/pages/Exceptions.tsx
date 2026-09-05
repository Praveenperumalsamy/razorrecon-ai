import React, { useEffect, useState } from 'react';
import { getExceptions, approveException, rejectException } from '../services/api';
import { ExceptionItem } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { ConfidenceBar } from '../components/ConfidenceBar';
import { AlertTriangle, Check, X, ArrowRight, Bot } from 'lucide-react';

export const Exceptions: React.FC = () => {
  const [exceptions, setExceptions] = useState<ExceptionItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchExceptions = async () => {
    try {
      setLoading(true);
      const res = await getExceptions();
      setExceptions(res.data);
    } catch (error) {
      console.error('Failed to fetch exceptions', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExceptions();
  }, []);

  const handleApprove = async (id: string) => {
    try {
      await approveException(id);
      fetchExceptions();
    } catch (error) {
      console.error('Failed to approve', error);
    }
  };

  const handleReject = async (id: string) => {
    try {
      await rejectException(id);
      fetchExceptions();
    } catch (error) {
      console.error('Failed to reject', error);
    }
  };

const formatCurrency = (amount: number, currency?: string) => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency || 'INR',
  }).format(amount);
};

  if (loading) {
    return <div className="space-y-4">
      {[1,2,3].map(i => <div key={i} className="animate-pulse bg-navy-800/50 h-48 rounded-2xl"></div>)}
    </div>;
  }

  if (exceptions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-96 bg-navy-800/50 rounded-2xl border border-white/5">
        <AlertTriangle size={48} className="text-emerald-500 mb-4 opacity-50" />
        <h3 className="text-xl font-medium text-white mb-2">No Exceptions Queue</h3>
        <p className="text-slate-400">All exceptions have been processed.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {exceptions.map(exc => (
        <div key={exc.id} className="bg-navy-800/50 backdrop-blur-xl border border-rose-500/20 rounded-2xl overflow-hidden transition-all duration-300 hover:border-rose-500/40 hover:shadow-lg hover:shadow-rose-500/5">
          <div className="p-6 border-b border-white/5 flex flex-col md:flex-row justify-between md:items-center gap-4">
            <div className="flex items-center gap-4">
              <div className="bg-rose-500/20 p-3 rounded-xl text-rose-400">
                <AlertTriangle size={24} />
              </div>
              <div>
                <div className="flex items-center gap-3 mb-1">
                  <h3 className="text-lg font-semibold text-white">{exc.payment_id}</h3>
                  <StatusBadge status="exception" />
                  <span className="text-xs bg-navy-700 text-slate-300 px-2 py-1 rounded-full">{exc.exception_type.replace('_', ' ').toUpperCase()}</span>
                </div>
                <p className="text-sm text-slate-400">Transaction ID: {exc.transaction_id}</p>
              </div>
            </div>
            
            <div className="flex gap-3">
              <button 
                onClick={() => handleReject(exc.id)}
                className="flex items-center gap-2 px-4 py-2 bg-navy-700 hover:bg-rose-500/20 text-rose-400 hover:text-rose-300 rounded-xl text-sm font-medium transition-colors"
              >
                <X size={16} /> Reject Match
              </button>
              <button 
                onClick={() => handleApprove(exc.id)}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 rounded-xl text-sm font-medium transition-colors"
              >
                <Check size={16} /> Force Approve
              </button>
            </div>
          </div>

          <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="space-y-4">
              <h4 className="text-sm font-medium text-slate-400 uppercase tracking-wider">Discrepancy Details</h4>
              <div className="bg-navy-900/50 rounded-xl p-4 border border-white/5 space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-slate-400 text-sm">Expected Amount</span>
                  <span className="text-white font-medium">{formatCurrency(exc.expected_amount, exc.currency)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400 text-sm">Actual Amount</span>
                  <span className="text-rose-400 font-medium">{formatCurrency(exc.actual_amount, exc.currency)}</span>
                </div>
                <div className="h-px bg-white/5 my-2"></div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400 text-sm">Difference</span>
                  <span className="text-white font-bold">{formatCurrency(Math.abs(exc.difference), exc.currency)}</span>
                </div>
                {exc.date_difference_days > 0 && (
                  <div className="flex justify-between items-center mt-2">
                    <span className="text-slate-400 text-sm">Date Mismatch</span>
                    <span className="text-amber-400 font-medium">{exc.date_difference_days} days</span>
                  </div>
                )}
              </div>
            </div>

            <div className="lg:col-span-2 space-y-4">
              <h4 className="flex items-center gap-2 text-sm font-medium text-blue-400 uppercase tracking-wider">
                <Bot size={16} /> AI Controller Analysis
              </h4>
              <div className="bg-blue-500/5 rounded-xl p-4 border border-blue-500/20">
                <div className="mb-4">
                  <div className="flex justify-between items-end mb-2">
                    <span className="text-white text-sm font-medium">Confidence Score</span>
                  </div>
                  <ConfidenceBar confidence={exc.ai_confidence} />
                </div>
                
                <p className="text-slate-300 text-sm leading-relaxed mb-4">
                  {exc.ai_explanation}
                </p>

                <div className="space-y-2 mb-4">
                  <span className="text-xs font-medium text-slate-500 uppercase">Evidence</span>
                  <ul className="space-y-1">
                    {exc.ai_evidence.map((ev, i) => (
                      <li key={i} className="text-sm text-slate-400 flex items-start gap-2">
                        <span className="text-blue-500 mt-0.5">•</span> {ev}
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="bg-blue-500/10 rounded-lg p-3 inline-block">
                  <span className="text-xs text-blue-400 font-medium uppercase tracking-wider block mb-1">Recommended Action</span>
                  <span className="text-white text-sm">{exc.recommended_action}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};
