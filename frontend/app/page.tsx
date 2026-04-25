'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { analyzeInput } from '@/lib/api';

export default function HomePage() {
  const router = useRouter();
  const [jdText, setJdText] = useState('');
  const [resumeText, setResumeText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!jdText.trim() || !resumeText.trim()) {
      setError('Please fill in both fields.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await analyzeInput(jdText, resumeText);
      const params = new URLSearchParams({
        first: data.first_message,
        skills: JSON.stringify(data.required_skills),
      });
      router.push(`/assess/${data.session_id}?${params.toString()}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to analyze. Please try again.');
      setLoading(false);
    }
  }

  return (
    <main className="max-w-4xl mx-auto px-4 py-12">
      <div className="text-center mb-10">
        <h1 className="text-4xl font-bold text-gray-900 mb-3">Skill Assessment Agent</h1>
        <p className="text-lg text-gray-500 max-w-2xl mx-auto">
          Paste a job description and your resume. Our AI interviewer will assess your real proficiency
          through conversation and generate a personalized learning plan.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6 bg-white p-8 rounded-2xl border border-gray-200 shadow-sm">
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Job Description <span className="text-red-500">*</span>
          </label>
          <textarea
            value={jdText}
            onChange={e => setJdText(e.target.value)}
            placeholder="Paste the full job description here..."
            rows={8}
            className="w-full p-4 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-sm text-gray-800"
          />
        </div>

        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Your Resume <span className="text-red-500">*</span>
          </label>
          <textarea
            value={resumeText}
            onChange={e => setResumeText(e.target.value)}
            placeholder="Paste your resume text here (copy-paste from PDF or Word)..."
            rows={8}
            className="w-full p-4 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-sm text-gray-800"
          />
        </div>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full py-4 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-semibold rounded-xl transition-colors text-base"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              Analyzing your profile...
            </span>
          ) : 'Start Skill Assessment'}
        </button>
      </form>

      <div className="mt-10 grid grid-cols-3 gap-4 text-center">
        {[
          { step: '1', title: 'Input', desc: 'Paste JD + Resume' },
          { step: '2', title: 'Assess', desc: 'Chat with AI interviewer' },
          { step: '3', title: 'Report', desc: 'Get your learning plan' },
        ].map(item => (
          <div key={item.step} className="p-5 bg-white rounded-xl border border-gray-200">
            <div className="w-9 h-9 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center font-bold mx-auto mb-3 text-sm">
              {item.step}
            </div>
            <h3 className="font-semibold text-gray-900 text-sm">{item.title}</h3>
            <p className="text-xs text-gray-500 mt-1">{item.desc}</p>
          </div>
        ))}
      </div>
    </main>
  );
}
