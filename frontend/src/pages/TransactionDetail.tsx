import React, { useEffect, useState } from 'react';

import { getTransactionDetail } from '../services/api';
import { TransactionDetail as TxDetailType } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { ConfidenceBar } from '../components/ConfidenceBar';

import {
  ArrowLeft,
  Bot,
  Building2,
  Database,
  CreditCard,
  History,
  AlertCircle,
  Check,
} from 'lucide-react';

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
} from 'recharts';

interface TransactionDetailProps {
  id: string;
  onBack: () => void;
}

export const TransactionDetail: React.FC<TransactionDetailProps> = ({ id, onBack }) => {
  const [detail, setDetail] = useState<TxDetailType | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDetail = async () => {
      try {
        setLoading(true);

        if (!id) {
          setDetail(null);
          return;
        }

        const res = await getTransactionDetail(id);
        setDetail(res.data);
      } catch (error) {
        console.error('Failed to fetch transaction details:', error);
        setDetail(null);
      } finally {
        setLoading(false);
      }
    };

    fetchDetail();
  }, [id]);

  // Loading state
  if (loading) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="h-24 bg-navy-800/50 rounded-2xl" />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="h-64 bg-navy-800/50 rounded-2xl" />
          <div className="h-64 bg-navy-800/50 rounded-2xl" />
        </div>
      </div>
    );
  }

  // Not found state
  if (!detail) {
    return (
      <div className="text-slate-400">
        Transaction not found
      </div>
    );
  }

  const {
    transaction,
    ai_analysis,
    score_breakdown,
    bank_record,
    ledger_record,
    settlement_record,
    audit_history,
  } = detail;

  // Score chart data
  const scoreData = Object.entries(score_breakdown).map(
    ([key, value]) => ({
      name: key
        .split('_')
        .map(
          (word) =>
            word.charAt(0).toUpperCase() + word.slice(1)
        )
        .join(' '),

      score: Math.round(Number(value) * 100),
    })
  );

  // Currency formatter
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: transaction.currency,
    }).format(amount);
  };

  // Source record card
  const renderRecordCard = (
    title: string,
    icon: React.ReactNode,
    record: Record<string, any> | null,
    borderColor: string
  ) => {
    if (!record) {
      return null;
    }

    return (
      <div
        className={`bg-navy-800/30 rounded-xl p-5 border ${borderColor}`}
      >
        <div className="flex items-center gap-2 mb-4 text-slate-300 font-medium">
          {icon}
          {title}
        </div>

        <div className="space-y-3">
          {Object.entries(record).map(([key, val]) => (
            <div
              key={key}
              className="flex justify-between text-sm"
            >
              <span className="text-slate-500 capitalize">
                {key.replace(/_/g, ' ')}
              </span>

              <span
                className="text-white font-medium text-right max-w-[60%] truncate"
                title={String(val)}
              >
                {String(val)}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">

      {/* Back Button */}
      <button
        onClick={onBack}
        className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors text-sm font-medium mb-4"
      >
        <ArrowLeft size={16} />
        Back to Reconciliation
      </button>

      {/* Header Card */}
      <div className="bg-navy-800/50 backdrop-blur-xl border border-white/10 rounded-2xl p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">

        <div>
          <div className="flex items-center gap-3 mb-2">
            <h2 className="text-2xl font-bold text-white">
              {transaction.payment_id}
            </h2>

            <StatusBadge status={transaction.status} />
          </div>

          <p className="text-slate-400 text-sm">
            ID: {transaction.id} •{' '}
            {new Date(transaction.date).toLocaleDateString()}
          </p>
        </div>

        <div className="flex gap-8 text-right">

          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">
              Bank Amount
            </p>

            <p className="text-xl font-semibold text-white">
              {formatCurrency(transaction.bank_amount)}
            </p>
          </div>

          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">
              Ledger Amount
            </p>

            <p className="text-xl font-semibold text-white">
              {formatCurrency(transaction.ledger_amount)}
            </p>
          </div>

        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* LEFT COLUMN */}
        <div className="lg:col-span-2 space-y-6">

          {/* Source Records */}
          <div className="bg-navy-800/50 backdrop-blur-xl border border-white/10 rounded-2xl p-6">

            <h3 className="text-lg font-medium text-white mb-6">
              Source Records Comparison
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

              {renderRecordCard(
                'Bank Statement',
                <Building2
                  size={18}
                  className="text-blue-400"
                />,
                bank_record,
                'border-blue-500/20'
              )}

              {renderRecordCard(
                'Internal Ledger',
                <Database
                  size={18}
                  className="text-emerald-400"
                />,
                ledger_record,
                'border-emerald-500/20'
              )}

              {renderRecordCard(
                'Payment Gateway',
                <CreditCard
                  size={18}
                  className="text-purple-400"
                />,
                settlement_record,
                'border-purple-500/20'
              )}

            </div>
          </div>

          {/* Audit History */}
          <div className="bg-navy-800/50 backdrop-blur-xl border border-white/10 rounded-2xl p-6">

            <h3 className="flex items-center gap-2 text-lg font-medium text-white mb-6">
              <History
                size={20}
                className="text-slate-400"
              />

              Audit History
            </h3>

            <div className="space-y-6 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-white/10 before:to-transparent">

              {audit_history.map((entry, idx) => (

                <div
                  key={idx}
                  className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active"
                >

                  <div className="flex items-center justify-center w-10 h-10 rounded-full border-4 border-navy-900 bg-navy-800 text-slate-400 group-[.is-active]:text-blue-400 shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2">

                    {entry.agent === 'system' ? (
                      <Bot size={16} />
                    ) : (
                      <div className="w-2 h-2 rounded-full bg-current" />
                    )}

                  </div>

                  <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] bg-navy-800/50 p-4 rounded-xl border border-white/5">

                    <div className="flex items-center justify-between mb-1">

                      <span className="font-medium text-white text-sm">
                        {entry.action.replace(/_/g, ' ')}
                      </span>

                      <time className="text-xs text-slate-500">
                        {new Date(
                          entry.timestamp
                        ).toLocaleString()}
                      </time>

                    </div>

                    <p className="text-sm text-slate-400">
                      {entry.reason}
                    </p>

                    <div className="mt-2 text-xs text-slate-500 flex items-center gap-2">

                      <span className="bg-white/5 px-2 py-1 rounded">
                        Agent: {entry.agent}
                      </span>

                      {entry.confidence > 0 && (
                        <span className="bg-white/5 px-2 py-1 rounded">
                          Conf:{' '}
                          {Math.round(
                            entry.confidence * 100
                          )}
                          %
                        </span>
                      )}

                    </div>

                  </div>

                </div>

              ))}

            </div>
          </div>

        </div>

        {/* RIGHT COLUMN */}
        <div className="space-y-6">

          {/* AI Analysis */}
          {ai_analysis && (

            <div
              className={`bg-navy-800/50 backdrop-blur-xl border rounded-2xl p-6 ${
                ai_analysis.requires_human_review
                  ? 'border-amber-500/30'
                  : 'border-blue-500/20'
              }`}
            >

              <h3 className="flex items-center gap-2 text-lg font-medium text-white mb-6">
                <Bot
                  size={20}
                  className="text-blue-400"
                />

                AI Controller Analysis
              </h3>

              {/* Confidence */}
              <div className="mb-6">

                <div className="flex justify-between items-end mb-2">

                  <span className="text-slate-400 text-sm">
                    Overall Confidence
                  </span>

                  <span className="text-white font-medium">
                    {Math.round(
                      ai_analysis.confidence * 100
                    )}
                    %
                  </span>

                </div>

                <ConfidenceBar
                  confidence={ai_analysis.confidence}
                />

              </div>

              <div className="space-y-4 mb-6">

                {/* Classification */}
                <div>

                  <span className="text-xs text-slate-500 uppercase tracking-wider block mb-1">
                    Classification
                  </span>

                  <span className="inline-block px-2.5 py-1 bg-white/5 border border-white/10 rounded-lg text-sm text-white capitalize">
                    {ai_analysis.classification.replace(
                      '_',
                      ' '
                    )}
                  </span>

                </div>

                {/* Reasoning */}
                <div>

                  <span className="text-xs text-slate-500 uppercase tracking-wider block mb-1">
                    Reasoning
                  </span>

                  <p className="text-sm text-slate-300 leading-relaxed">
                    {ai_analysis.reason}
                  </p>

                </div>

                {/* Evidence */}
                <div>

                  <span className="text-xs text-slate-500 uppercase tracking-wider block mb-2">
                    Evidence
                  </span>

                  <ul className="space-y-2">

                    {ai_analysis.evidence.map(
                      (ev, i) => (

                        <li
                          key={i}
                          className="text-sm text-slate-400 flex items-start gap-2 bg-navy-900/50 p-2 rounded-lg"
                        >

                          <Check
                            size={14}
                            className="text-emerald-500 mt-0.5 shrink-0"
                          />

                          <span>{ev}</span>

                        </li>

                      )
                    )}

                  </ul>

                </div>

              </div>

              {/* Human Review */}
              {ai_analysis.requires_human_review && (

                <div className="flex items-start gap-3 bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 mb-6">

                  <AlertCircle
                    className="text-amber-500 shrink-0 mt-0.5"
                    size={18}
                  />

                  <div>

                    <h4 className="text-amber-500 font-medium text-sm">
                      Human Review Required
                    </h4>

                    <p className="text-amber-500/80 text-xs mt-1">
                      Confidence below threshold or
                      complex discrepancy detected.
                    </p>

                  </div>

                </div>

              )}

              {/* Recommended Action */}
              <div className="pt-4 border-t border-white/5">

                <span className="text-xs text-slate-500 uppercase tracking-wider block mb-2">
                  Recommended Action
                </span>

                <div className="bg-blue-500/10 text-blue-400 p-3 rounded-xl text-sm font-medium text-center border border-blue-500/20">
                  {ai_analysis.recommended_action}
                </div>

              </div>

            </div>
          )}

          {/* Score Breakdown */}
          <div className="bg-navy-800/50 backdrop-blur-xl border border-white/10 rounded-2xl p-6">

            <h3 className="text-lg font-medium text-white mb-6">
              Match Score Breakdown
            </h3>

            <div className="h-64">

              <ResponsiveContainer
                width="100%"
                height="100%"
              >

                <BarChart
                  data={scoreData}
                  layout="vertical"
                  margin={{
                    top: 0,
                    right: 0,
                    left: 0,
                    bottom: 0
                  }}
                >

                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="#334155"
                    horizontal={true}
                    vertical={false}
                  />

                  <XAxis
                    type="number"
                    domain={[0, 100]}
                    hide
                  />

                  <YAxis
                    dataKey="name"
                    type="category"
                    stroke="#94a3b8"
                    width={100}
                    tick={{ fontSize: 12 }}
                  />

                  <Tooltip
                    cursor={{
                      fill: '#334155',
                      opacity: 0.4
                    }}
                    contentStyle={{
                      backgroundColor: '#1E293B',
                      borderColor: '#334155',
                      borderRadius: '0.5rem',
                      color: '#fff'
                    }}
                    formatter={(value) => [
                      `${Number(value)}%`,
                      'Score'
                    ]}
                  />

                  <Bar
                    dataKey="score"
                    radius={[0, 4, 4, 0]}
                  >

                    {scoreData.map(
                      (entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={
                            entry.score > 90
                              ? '#10B981'
                              : entry.score > 75
                              ? '#F59E0B'
                              : '#F43F5E'
                          }
                        />
                      )
                    )}

                  </Bar>

                </BarChart>

              </ResponsiveContainer>

            </div>
          </div>

        </div>

      </div>
    </div>
  );
};