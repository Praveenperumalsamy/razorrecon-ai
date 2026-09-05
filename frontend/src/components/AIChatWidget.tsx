import React, { useState, useRef, useEffect } from 'react';
import { sendChatMessage } from '../services/api';
import { ChatMessage } from '../types';
import { Bot, User, Send, Sparkles, Loader2, X, MessageCircle } from 'lucide-react';

const QUICK_QUESTIONS = [
  'How much is unreconciled?',
  'Show highest risk exceptions',
  'How many auto-reconciled today?',
  'What is the match rate?',
];

export const AIChatWidget: React.FC = () => {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content:
        'Hi, I\'m RazorRecon AI. Ask me anything about your reconciliation data — I\'m available on every screen.',
      timestamp: new Date().toISOString(),
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, open]);

  const handleSend = async (text: string) => {
    if (!text.trim() || loading) return;

    const userMsg: ChatMessage = {
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await sendChatMessage(text);
      setMessages((prev) => [...prev, res.data]);
    } catch (error) {
      console.error('Chat error', error);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, I ran into an error reaching the AI service. Please try again.',
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Floating launcher button — bottom right, on top of everything */}
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? 'Close AI assistant' : 'Open AI assistant'}
        className="fixed bottom-6 right-6 z-50 flex items-center justify-center w-14 h-14 rounded-full bg-blue-500 hover:bg-blue-600 text-white shadow-lg shadow-blue-500/30 transition-transform hover:scale-105"
      >
        {open ? <X size={24} /> : <MessageCircle size={24} />}
      </button>

      {/* Chat panel */}
      {open && (
        <div className="fixed bottom-24 right-6 z-50 w-[92vw] max-w-sm h-[70vh] max-h-[560px] flex flex-col bg-navy-800/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl overflow-hidden">
          <div className="flex items-center gap-3 px-4 py-3 border-b border-white/10 bg-navy-900/60">
            <div className="w-8 h-8 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center">
              <Bot size={18} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-white truncate">RazorRecon AI</p>
              <p className="text-[11px] text-slate-400">Finance controller assistant</p>
            </div>
            <button
              onClick={() => setOpen(false)}
              className="text-slate-500 hover:text-white transition p-1"
              aria-label="Close"
            >
              <X size={18} />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((msg, idx) => (
              <div key={idx} className={`flex gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${
                    msg.role === 'user'
                      ? 'bg-blue-500 text-white'
                      : 'bg-navy-900 border border-blue-500/30 text-blue-400'
                  }`}
                >
                  {msg.role === 'user' ? <User size={14} /> : <Bot size={14} />}
                </div>
                <div className={`max-w-[80%] flex flex-col gap-1 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                  <div
                    className={`px-3 py-2 rounded-2xl text-xs leading-relaxed ${
                      msg.role === 'user'
                        ? 'bg-blue-500 text-white rounded-tr-sm'
                        : 'bg-navy-900/80 border border-white/5 text-slate-200 rounded-tl-sm'
                    }`}
                  >
                    {msg.content}
                  </div>
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex gap-2">
                <div className="w-7 h-7 rounded-full bg-navy-900 border border-blue-500/30 text-blue-400 flex items-center justify-center">
                  <Loader2 size={14} className="animate-spin" />
                </div>
                <div className="bg-navy-900/80 border border-white/5 text-slate-400 px-3 py-2 rounded-2xl rounded-tl-sm text-xs flex items-center gap-2">
                  <Sparkles size={13} className="text-blue-400 animate-pulse" /> Thinking...
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="border-t border-white/10 p-3 bg-navy-900/40">
            <div className="flex flex-wrap gap-1.5 mb-2">
              {QUICK_QUESTIONS.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(q)}
                  className="text-[11px] bg-white/5 hover:bg-blue-500/20 hover:text-blue-400 border border-white/10 rounded-full px-3 py-1.5 text-slate-400 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSend(input);
              }}
              className="flex items-center gap-2"
            >
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about your data..."
                className="flex-1 bg-navy-900/50 border border-white/10 rounded-xl px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors text-xs"
              />
              <button
                type="submit"
                disabled={!input.trim() || loading}
                className="bg-blue-500 hover:bg-blue-600 disabled:opacity-50 disabled:hover:bg-blue-500 text-white p-2.5 rounded-xl transition-colors"
              >
                <Send size={16} />
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  );
};
