'use client';
import { useState, useEffect, useRef } from 'react';
import { useRouter, useParams, useSearchParams } from 'next/navigation';
import { sendMessage } from '@/lib/api';
import type { ChatMessage } from '@/lib/types';

export default function AssessPage() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const sessionId = params.sessionId as string;

  const firstMessage = searchParams.get('first') || '';
  const skillsParam = searchParams.get('skills') || '[]';
  const skills: string[] = JSON.parse(decodeURIComponent(skillsParam));

  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'assistant', content: firstMessage }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [assessedCount, setAssessedCount] = useState(0);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (!loading) inputRef.current?.focus();
  }, [loading]);

  async function handleSend() {
    if (!input.trim() || loading || isComplete) return;
    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    // Add placeholder for streaming response
    setMessages(prev => [...prev, { role: 'assistant', content: '', streaming: true }]);

    let assistantContent = '';
    let done = false;

    try {
      for await (const chunk of sendMessage(sessionId, userMessage)) {
        if (chunk.token) {
          assistantContent += chunk.token;
          setMessages(prev => {
            const updated = [...prev];
            updated[updated.length - 1] = { role: 'assistant', content: assistantContent, streaming: true };
            return updated;
          });
        }
        if (chunk.is_complete) {
          done = true;
        }
      }
    } catch (err) {
      console.error('Assessment error:', err);
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = { role: 'assistant', content: 'Sorry, something went wrong. Please try again.' };
        return updated;
      });
    }

    // Mark streaming done
    setMessages(prev => {
      const updated = [...prev];
      if (updated[updated.length - 1].role === 'assistant') {
        updated[updated.length - 1] = { role: 'assistant', content: assistantContent };
      }
      return updated;
    });

    if (done) {
      setIsComplete(true);
      setAssessedCount(skills.length);
    } else {
      // Rough tracking: count agent turns as skill transitions
      setAssessedCount(prev => Math.min(prev + 0.5, skills.length - 1));
    }

    setLoading(false);
  }

  const progress = skills.length > 0 ? Math.round((assessedCount / skills.length) * 100) : 0;

  return (
    <main className="max-w-3xl mx-auto px-4 py-6 flex flex-col" style={{ height: '100dvh' }}>
      {/* Header */}
      <div className="mb-4 flex-shrink-0">
        <div className="flex justify-between items-center mb-2">
          <h1 className="text-sm font-semibold text-gray-700">Skill Assessment</h1>
          <span className="text-xs text-gray-400">{Math.round(assessedCount)}/{skills.length} skills</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-1.5">
          <div
            className="bg-blue-600 h-1.5 rounded-full transition-all duration-500"
            style={{ width: `${Math.max(5, progress)}%` }}
          />
        </div>
        <div className="flex gap-2 mt-2 flex-wrap">
          {skills.map(s => (
            <span key={s} className="text-xs px-2 py-0.5 bg-gray-100 text-gray-500 rounded-full">{s}</span>
          ))}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4 min-h-0">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] p-4 rounded-2xl text-sm leading-relaxed ${
              msg.role === 'user'
                ? 'bg-blue-600 text-white rounded-br-sm'
                : 'bg-white border border-gray-200 text-gray-800 rounded-bl-sm shadow-sm'
            }`}>
              {msg.content ? msg.content : (
                <span className="flex gap-1">
                  <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}/>
                  <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}/>
                  <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}/>
                </span>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="flex-shrink-0 pt-4 border-t border-gray-200">
        {isComplete ? (
          <div className="text-center space-y-2">
            <p className="text-sm text-gray-500">Assessment complete!</p>
            <button
              onClick={() => router.push(`/report/${sessionId}`)}
              className="w-full py-3 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-xl transition-colors"
            >
              View My Report & Learning Plan
            </button>
          </div>
        ) : (
          <div className="flex gap-3">
            <input
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
              placeholder={loading ? 'Waiting for response...' : 'Type your answer...'}
              disabled={loading}
              className="flex-1 p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm disabled:bg-gray-50 disabled:text-gray-400"
            />
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="px-5 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-200 text-white font-semibold rounded-xl transition-colors text-sm"
            >
              Send
            </button>
          </div>
        )}
      </div>
    </main>
  );
}
