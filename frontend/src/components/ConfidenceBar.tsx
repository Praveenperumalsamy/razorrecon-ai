import React from 'react';

interface ConfidenceBarProps {
  confidence: number; // 0 to 1
}

export const ConfidenceBar: React.FC<ConfidenceBarProps> = ({ confidence }) => {
  const percentage = Math.round(confidence * 100);
  let colorClass = 'bg-emerald-500';
  if (percentage < 75) {
    colorClass = 'bg-rose-500';
  } else if (percentage < 90) {
    colorClass = 'bg-amber-500';
  }

  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-2 bg-navy-900 rounded-full overflow-hidden border border-white/5">
        <div 
          className={`h-full rounded-full ${colorClass}`} 
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="text-xs font-medium text-slate-300 w-9 text-right">{percentage}%</span>
    </div>
  );
};
