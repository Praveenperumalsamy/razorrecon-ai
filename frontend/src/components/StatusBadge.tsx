import React from 'react';

interface StatusBadgeProps {
  status: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const getStyle = (s: string) => {
    switch (s.toLowerCase()) {
      case 'auto_reconciled':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'ai_review':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      case 'human_review':
      case 'escalated':
        return 'bg-rose-500/10 text-rose-400 border-rose-500/30';
      case 'manually_approved':
      case 'approved':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/30';
      case 'manually_rejected':
      case 'rejected':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/30';
      default:
        return 'bg-slate-500/10 text-slate-400 border-slate-500/30';
    }
  };

  const formatText = (s: string) => {
    return s.replace(/_/g, ' ').toUpperCase();
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${getStyle(
        status
      )}`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current mr-1.5 animate-pulse" />
      {formatText(status)}
    </span>
  );
};
