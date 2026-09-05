import React, { useEffect, useState } from 'react';
import { getEvaluation } from '../services/api';
import { EvaluationData } from '../types';
import { KPICard } from '../components/KPICard';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Target, Search, Crosshair, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
export const Evaluation: React.FC = () => {
  const [data, setData] = useState<EvaluationData | null>(null);
  
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchEval = async () => {
      try {
        setLoading(true);
        const res = await getEvaluation();
        setData(res.data);
      } catch (error) {
        console.error('Failed to fetch evaluation', error);
      } finally {
        setLoading(false);
      }
    };
    fetchEval();
  }, []);

  if (loading) {
    return <div className="animate-pulse space-y-6">
      <div className="h-32 bg-navy-800/50 rounded-2xl"></div>
      <div className="grid grid-cols-4 gap-6"><div className="h-32 bg-navy-800/50 rounded-2xl"></div><div className="h-32 bg-navy-800/50 rounded-2xl"></div><div className="h-32 bg-navy-800/50 rounded-2xl"></div><div className="h-32 bg-navy-800/50 rounded-2xl"></div></div>
    </div>;
  }

  if (!data) return <div className="text-slate-400">No evaluation data available</div>;

if (!data) return <div className="text-slate-400">No evaluation data available</div>;

const formatCurrency = (amount: number) => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'INR',
  }).format(amount);
};
  const chartData = [
    { name: 'Precision', value: Math.round(data.precision * 100) },
    { name: 'Recall', value: Math.round(data.recall * 100) },
    { name: 'F1 Score', value: Math.round(data.f1_score * 100) },
  ];

  const cm = data.confusion_matrix;
  const total = cm.true_positives + cm.false_positives + cm.true_negatives + cm.false_negatives;

  return (
    <div className="space-y-8 pb-12">
      <div className="bg-navy-800/30 backdrop-blur-xl border border-blue-500/20 rounded-2xl p-6">
        <h2 className="text-xl font-semibold text-white mb-2">Model Evaluation on Synthetic Held-Out Set</h2>
        <p className="text-slate-400 text-sm">These metrics measure the performance of the AI Controller against a ground-truth dataset.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <KPICard 
          title="Precision" 
          value={`${(data.precision * 100).toFixed(1)}%`} 
          icon={<Target size={20} />} 
          subtitle="When AI predicts a match, it is correct this often"
          trend={data.precision > 0.95 ? 'up' : 'down'}
        />
        <KPICard 
          title="Recall" 
          value={`${(data.recall * 100).toFixed(1)}%`} 
          icon={<Search size={20} />} 
          subtitle="Of all true matches, AI finds this many"
          trend={data.recall > 0.90 ? 'up' : 'down'}
        />
        <KPICard 
          title="F1 Score" 
          value={`${(data.f1_score * 100).toFixed(1)}%`} 
          icon={<Crosshair size={20} />} 
          subtitle="Harmonic mean of Precision and Recall"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Confusion Matrix */}
        <div className="bg-navy-800/50 backdrop-blur-xl border border-white/10 rounded-2xl p-6">
          <h3 className="text-lg font-medium text-white mb-6">Confusion Matrix</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-emerald-500/10 border border-emerald-500/20 p-4 rounded-xl">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-emerald-400">True Positives</span>
                <CheckCircle size={16} className="text-emerald-500" />
              </div>
              <p className="text-2xl font-bold text-white">{cm.true_positives}</p>
              <p className="text-xs text-emerald-400/70 mt-1">Correctly matched</p>
            </div>
            <div className="bg-rose-500/10 border border-rose-500/20 p-4 rounded-xl">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-rose-400">False Positives</span>
                <AlertTriangle size={16} className="text-rose-500" />
              </div>
              <p className="text-2xl font-bold text-white">{cm.false_positives}</p>
              <p className="text-xs text-rose-400/70 mt-1">Incorrectly matched (Risk!)</p>
            </div>
            <div className="bg-amber-500/10 border border-amber-500/20 p-4 rounded-xl">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-amber-400">False Negatives</span>
                <XCircle size={16} className="text-amber-500" />
              </div>
              <p className="text-2xl font-bold text-white">{cm.false_negatives}</p>
              <p className="text-xs text-amber-400/70 mt-1">Missed matches</p>
            </div>
            <div className="bg-slate-700/30 border border-slate-600/30 p-4 rounded-xl">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-slate-400">True Negatives</span>
                <CheckCircle size={16} className="text-slate-500" />
              </div>
              <p className="text-2xl font-bold text-white">{cm.true_negatives}</p>
              <p className="text-xs text-slate-400/70 mt-1">Correctly left unmatched</p>
            </div>
          </div>
        </div>

        {/* Risk Assessment */}
        <div className="space-y-6">
          <div className="bg-rose-500/5 backdrop-blur-xl border border-rose-500/20 rounded-2xl p-6">
            <h3 className="flex items-center gap-2 text-lg font-medium text-rose-400 mb-6">
              <AlertTriangle size={20} /> False Positive Risk Assessment
            </h3>
            <div className="space-y-4">
              <div className="flex justify-between items-center bg-navy-900/50 p-4 rounded-xl border border-rose-500/10">
                <span className="text-slate-300">False Positive Rate</span>
                <span className="text-rose-400 font-bold text-lg">{(data.false_positive_rate * 100).toFixed(2)}%</span>
              </div>
              <div className="flex justify-between items-center bg-navy-900/50 p-4 rounded-xl border border-rose-500/10">
                <span className="text-slate-300">Incorrectly Reconciled Amount</span>
                <span className="text-rose-400 font-bold text-lg">{formatCurrency(data.false_positive_amount)}</span>
              </div>
            </div>
            <p className="text-xs text-slate-400 mt-4">
              False positives represent financial exposure where the system incorrectly assumed two records matched when they did not.
            </p>
          </div>

          <div className="bg-navy-800/50 backdrop-blur-xl border border-white/10 rounded-2xl p-6">
            <h3 className="text-lg font-medium text-white mb-6">Performance Profile</h3>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis dataKey="name" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" domain={[0, 100]} />
                  <Tooltip 
                    cursor={{fill: '#334155', opacity: 0.4}}
                    contentStyle={{ backgroundColor: '#1E293B', borderColor: '#334155', borderRadius: '0.5rem', color: '#fff' }}
formatter={(value) => [`${value}%`, 'Score']}                  />
                  <Bar dataKey="value" fill="#3B82F6" radius={[4, 4, 0, 0]} barSize={40} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
