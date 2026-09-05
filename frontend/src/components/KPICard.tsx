import React from 'react';

interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  trend?: string;
  trendValue?: string;
  badgeColor?: 'blue' | 'emerald' | 'amber' | 'rose';
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  subtitle,
  icon,
  trend,
  trendValue,
  badgeColor = 'blue',
}) => {
  const borderColors = {
    blue: 'hover:border-blue-500/40',
    emerald: 'hover:border-emerald-500/40',
    amber: 'hover:border-amber-500/40',
    rose: 'hover:border-rose-500/40',
  };

  const trendColor = trend === 'up' ? 'text-emerald-400' : trend === 'down' ? 'text-rose-400' : 'text-slate-400';

  return (
    <div
      className={`bg-slate-900/60 backdrop-blur-xl border border-slate-800 rounded-2xl p-5 transition-all duration-300 ${borderColors[badgeColor]} hover:shadow-xl hover:shadow-blue-500/5 group`}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          {title}
        </span>
        {icon && (
          <div className="p-2 rounded-xl bg-slate-800/80 text-blue-400 group-hover:scale-110 transition-transform">
            {icon}
          </div>
        )}
      </div>
      <div className="text-3xl font-extrabold tracking-tight text-white font-mono mb-1">
        {value}
      </div>
      <div className="flex items-center gap-2">
        {subtitle && <div className="text-xs text-slate-400">{subtitle}</div>}
        {trendValue && <div className={`text-xs font-semibold ${trendColor}`}>{trendValue}</div>}
      </div>
    </div>
  );
};
