import React, { useEffect, useState } from 'react';
import { getDashboard, runDemo } from '../services/api';
import { DashboardData } from '../types';
import { KPICard } from '../components/KPICard';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from 'recharts';
import {
  Database,
  CheckCircle,
  Bot,
  Zap,
  Users,
  AlertCircle,
  Percent,
  DollarSign,
  Play
} from 'lucide-react';
export const Dashboard: React.FC = () => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [demoLoading, setDemoLoading] = useState(false);

  const fetchData = async () => {
    try {
      setLoading(true);
      const res = await getDashboard();
      setData(res.data);
    } catch (error) {
      console.error('Failed to fetch dashboard data', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRunDemo = async () => {
    try {
      setDemoLoading(true);
      await runDemo();
      await fetchData();
    } catch (error) {
      console.error('Failed to run demo', error);
    } finally {
      setDemoLoading(false);
    }
  };

  if (loading) {
    return <div className="animate-pulse space-y-6">
      <div className="h-32 bg-navy-800/50 rounded-2xl"></div>
      <div className="grid grid-cols-4 gap-6">
        {[1,2,3,4,5,6,7,8].map(i => <div key={i} className="h-32 bg-navy-800/50 rounded-2xl"></div>)}
      </div>
    </div>;
  }

  if (!data) return <div className="text-slate-400">No data available</div>;

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: data.currency }).format(amount);
  };

  const statusData = [
    { name: 'Auto-Reconciled', value: data.auto_reconciled, color: '#10B981' }, // Emerald
    { name: 'AI Assisted', value: data.ai_assisted, color: '#F59E0B' }, // Amber
    { name: 'Human Review', value: data.human_review, color: '#3B82F6' }, // Blue
    { name: 'Exceptions', value: data.exceptions, color: '#F43F5E' }, // Rose
  ];

  return (
    <div className="space-y-8 pb-12">
      <div className="flex justify-between items-center bg-navy-800/30 p-6 rounded-2xl border border-blue-500/20">
        <div>
          <h3 className="text-lg font-semibold text-white mb-1">Interactive Demo Mode</h3>
          <p className="text-slate-400 text-sm">Generate synthetic data and run the full AI reconciliation pipeline.</p>
        </div>
        <button 
          onClick={handleRunDemo}
          disabled={demoLoading}
          className="flex items-center gap-2 bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded-xl font-medium transition-all duration-300 disabled:opacity-50"
        >
          {demoLoading ? <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Play size={18} fill="currentColor" />}
          {demoLoading ? 'Processing...' : 'Run Pipeline Demo'}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KPICard title="Total Records" value={data.total_records.toLocaleString()} icon={<Database size={20} />} />
        <KPICard title="Reconciled" value={data.reconciled.toLocaleString()} icon={<CheckCircle size={20} />} trend="up" trendValue={`${(data.reconciled/Math.max(1, data.total_records)*100).toFixed(1)}%`} />
        <KPICard title="Auto-Reconciled" value={data.auto_reconciled.toLocaleString()} icon={<Bot size={20} />} subtitle="No human intervention" />
        <KPICard title="AI Assisted" value={data.ai_assisted.toLocaleString()} icon={<Zap size={20} />} subtitle="Matched by AI Controller" />
        <KPICard title="Human Review" value={data.human_review.toLocaleString()} icon={<Users size={20} />} />
        <KPICard title="Exceptions" value={data.exceptions.toLocaleString()} icon={<AlertCircle size={20} />} trend={data.exceptions > 0 ? 'down' : 'neutral'} />
        <KPICard title="Match Rate" value={`${(data.match_rate * 100).toFixed(1)}%`} icon={<Percent size={20} />} />
        <KPICard title="Reconciled Amount" value={formatCurrency(data.reconciled_amount)} subtitle={`of ${formatCurrency(data.total_amount)}`} icon={<DollarSign size={20} />} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-navy-800/50 backdrop-blur-xl border border-white/10 rounded-2xl p-6">
          <h3 className="text-lg font-medium text-white mb-6">Reconciliation Breakdown</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={statusData} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={true} vertical={false} />
                <XAxis type="number" stroke="#94a3b8" />
                <YAxis dataKey="name" type="category" stroke="#94a3b8" width={120} />
                <RechartsTooltip 
                  contentStyle={{ backgroundColor: '#1E293B', borderColor: '#334155', borderRadius: '0.5rem', color: '#fff' }}
                  itemStyle={{ color: '#fff' }}
                />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {statusData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-navy-800/50 backdrop-blur-xl border border-white/10 rounded-2xl p-6">
          <h3 className="text-lg font-medium text-white mb-6">Status Distribution</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={statusData.filter(d => d.value > 0)}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {statusData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <RechartsTooltip 
                  contentStyle={{ backgroundColor: '#1E293B', borderColor: '#334155', borderRadius: '0.5rem', color: '#fff' }}
                  itemStyle={{ color: '#fff' }}
                />
                <Legend verticalAlign="bottom" height={36} iconType="circle" />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};
