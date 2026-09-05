import React, { useEffect } from 'react';
import { CheckCircle, AlertCircle, X } from 'lucide-react';

export interface ToastData {
  type: 'success' | 'error';
  message: string;
  actionLabel?: string;
  onAction?: () => void;
}

interface ToastProps extends ToastData {
  onClose: () => void;
  duration?: number;
}

export const Toast: React.FC<ToastProps> = ({
  type,
  message,
  actionLabel,
  onAction,
  onClose,
  duration = 4000,
}) => {
  useEffect(() => {
    const timer = setTimeout(onClose, duration);
    return () => clearTimeout(timer);
  }, [onClose, duration]);

  const isSuccess = type === 'success';

  return (
    <div
      role="status"
      className={`fixed top-6 right-6 z-50 flex items-center gap-3 rounded-xl border px-4 py-3.5 shadow-2xl backdrop-blur-xl animate-in fade-in slide-in-from-top-2 duration-300 ${
        isSuccess
          ? 'bg-emerald-500/10 border-emerald-500/20'
          : 'bg-rose-500/10 border-rose-500/20'
      }`}
    >
      {isSuccess ? (
        <CheckCircle className="text-emerald-400 shrink-0" size={20} />
      ) : (
        <AlertCircle className="text-rose-400 shrink-0" size={20} />
      )}

      <p
        className={`text-sm font-medium ${
          isSuccess ? 'text-emerald-300' : 'text-rose-300'
        }`}
      >
        {message}
      </p>

      {actionLabel && onAction && (
        <button
          type="button"
          onClick={onAction}
          className={`text-sm font-semibold underline underline-offset-2 shrink-0 ${
            isSuccess ? 'text-emerald-300 hover:text-emerald-200' : 'text-rose-300 hover:text-rose-200'
          }`}
        >
          {actionLabel}
        </button>
      )}

      <button
        type="button"
        onClick={onClose}
        className="text-slate-400 hover:text-white shrink-0"
        aria-label="Dismiss"
      >
        <X size={16} />
      </button>
    </div>
  );
};