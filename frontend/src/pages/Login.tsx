import React, { useState } from 'react';
import { Zap, AlertCircle, Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { registerUser } from '../services/api';

export const Login: React.FC = () => {
  const { login } = useAuth();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // App.tsx only renders Login when there is no authenticated user, and
  // swaps in the main app the moment `login()` below succeeds — so no
  // redirect is needed here.

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (mode === 'register') {
        await registerUser(email, password, fullName || undefined);
      }
      await login(email, password);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center h-screen bg-navy-900 text-slate-200 relative overflow-hidden">
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-blue-500/10 blur-[120px] rounded-full pointer-events-none" />

      <div className="w-full max-w-sm bg-navy-800 border border-white/5 rounded-2xl p-8 z-10">
        <div className="flex items-center gap-3 mb-8">
          <div className="bg-blue-500/20 text-blue-400 p-2 rounded-xl">
            <Zap size={24} className="fill-current" />
          </div>
          <div>
            <h1 className="font-bold text-lg text-white tracking-tight">RazorRecon AI</h1>
            <p className="text-xs text-blue-400 font-medium">AI Finance Controller</p>
          </div>
        </div>

        <div className="flex mb-6 rounded-xl bg-white/5 p-1">
          <button
            type="button"
            onClick={() => setMode('login')}
            className={`flex-1 py-2 text-sm font-medium rounded-lg transition ${mode === 'login' ? 'bg-blue-500/20 text-blue-400' : 'text-slate-400'}`}
          >
            Sign in
          </button>
          <button
            type="button"
            onClick={() => setMode('register')}
            className={`flex-1 py-2 text-sm font-medium rounded-lg transition ${mode === 'register' ? 'bg-blue-500/20 text-blue-400' : 'text-slate-400'}`}
          >
            Create account
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === 'register' && (
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Full name</label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500/50"
                placeholder="Jane Doe"
              />
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500/50"
              placeholder="you@company.com"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Password</label>
            <input
              type="password"
              required
              minLength={mode === 'register' ? 10 : undefined}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500/50"
              placeholder="••••••••••"
            />
            {mode === 'register' && (
              <p className="text-[11px] text-slate-500 mt-1">Minimum 10 characters.</p>
            )}
          </div>

          {error && (
            <div className="flex items-start gap-2 text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
              <AlertCircle size={16} className="mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 bg-blue-500 hover:bg-blue-400 disabled:opacity-60 text-white font-medium text-sm rounded-lg py-2.5 transition"
          >
            {loading && <Loader2 size={16} className="animate-spin" />}
            {mode === 'login' ? 'Sign in' : 'Create account'}
          </button>
        </form>

        <p className="text-[11px] text-slate-500 mt-6 text-center">
          The first account created on a fresh deployment is automatically granted admin access.
        </p>
      </div>
    </div>
  );
};
