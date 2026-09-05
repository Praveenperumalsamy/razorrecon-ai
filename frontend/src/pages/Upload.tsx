import React, { useState } from 'react';
import { useAppNav } from '../context/NavContext';
import { uploadFiles, runReconciliation } from '../services/api';
import { Toast, ToastData } from '../components/Toast';

import { UploadCloud, FileText } from 'lucide-react';

interface ReconcileSummary {
  total_records: number;
  reconciled: number;
  exceptions: number;
  match_rate: number;
  execution_time_seconds: number;
}

interface ReconcileResult {
  summary?: ReconcileSummary;
  error?: string;
}

export const Upload: React.FC = () => {
  const [files, setFiles] = useState<Record<string, File | null>>({
    bank: null,
    settlement: null,
    ledger: null,
    refund: null,
    chargeback: null,
  });

  const [uploading, setUploading] = useState(false);
  const [toast, setToast] = useState<ToastData | null>(null);
  const { goToTab } = useAppNav();

  const handleFileChange = (
    type: string,
    file: File | null
  ) => {
    setFiles((prev) => ({
      ...prev,
      [type]: file,
    }));
  };

  const handleUpload = async () => {
    const formData = new FormData();

    Object.entries(files).forEach(([key, file]) => {
      if (file) {
        formData.append(`${key}_file`, file);
      }
    });

    try {
      setUploading(true);
      setToast(null);

      await uploadFiles(formData);

      const reconcileRes = await runReconciliation();
      const data: ReconcileResult = reconcileRes.data;

      if (data.error) {
        setToast({ type: 'error', message: data.error });
        return;
      }

      const summary = data.summary;

      setToast({
        type: 'success',
        message: summary
          ? `Upload successful — ${summary.total_records.toLocaleString()} records processed, ${summary.match_rate.toFixed(1)}% matched.`
          : 'Upload successful.',
        actionLabel: 'View Reconciliation',
        onAction: () => goToTab('reconciliation'),
      });
    } catch (error) {
      console.error(
        'Upload or reconciliation failed:',
        error
      );

      setToast({
        type: 'error',
        message: 'Upload failed. Please try again.',
      });
    } finally {
      setUploading(false);
    }
  };

  const fileTypes = [
    {
      id: 'bank',
      label: 'Bank Transactions',
      desc: 'CSV from banking provider',
    },
    {
      id: 'settlement',
      label: 'Settlements',
      desc: 'CSV from payment gateway',
    },
    {
      id: 'ledger',
      label: 'Internal Ledger',
      desc: 'Internal database export',
    },
    {
      id: 'refund',
      label: 'Refunds',
      desc: 'Optional: Refund records',
    },
    {
      id: 'chargeback',
      label: 'Chargebacks',
      desc: 'Optional: Chargeback records',
    },
  ];

  return (
    <div className="space-y-6">

      {toast && (
        <Toast
          type={toast.type}
          message={toast.message}
          actionLabel={toast.actionLabel}
          onAction={toast.onAction}
          onClose={() => setToast(null)}
        />
      )}

      {/* Upload Section */}
      <div className="bg-navy-900/40 border border-white/5 rounded-2xl p-6">

        <div className="flex items-center gap-3 mb-6">
          <UploadCloud
            className="text-blue-400"
            size={24}
          />

          <div>
            <h2 className="text-xl font-semibold text-white">
              Upload Files
            </h2>

            <p className="text-sm text-slate-400">
              Upload your reconciliation data files
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">

          {fileTypes.map((type) => (
            <label
              key={type.id}
              className="border border-white/10 rounded-xl p-4 cursor-pointer hover:border-blue-500/50 transition-colors"
            >
              <div className="flex items-center gap-3 mb-2">

                <FileText
                  className="text-slate-400"
                  size={20}
                />

                <span className="text-white font-medium">
                  {type.label}
                </span>

              </div>

              <p className="text-xs text-slate-500 mb-3">
                {type.desc}
              </p>

              <input
                type="file"
                accept=".csv,.xlsx,.xls"
                className="block w-full text-sm text-slate-400"
                onChange={(e) =>
                  handleFileChange(
                    type.id,
                    e.target.files?.[0] || null
                  )
                }
              />

              {files[type.id] && (
                <p className="text-xs text-emerald-400 mt-2 truncate">
                  {files[type.id]?.name}
                </p>
              )}
            </label>
          ))}

        </div>

        <button
          type="button"
          onClick={handleUpload}
          disabled={uploading}
          className="mt-6 flex items-center gap-2 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-500/50 disabled:cursor-not-allowed text-white px-5 py-2.5 rounded-xl font-medium transition-colors"
        >
          <UploadCloud size={18} />

          {uploading
            ? 'Uploading & Reconciling...'
            : 'Upload & Reconcile'}
        </button>

      </div>

    </div>
  );
};