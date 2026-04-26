'use client';
import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { analyzeWithFiles } from '@/lib/api';

const ACCEPT = '.pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document';

function InputField({
  label,
  mode,
  onModeChange,
  text,
  onTextChange,
  file,
  onFileChange,
  placeholder,
}: {
  label: string;
  mode: 'write' | 'upload';
  onModeChange: (m: 'write' | 'upload') => void;
  text: string;
  onTextChange: (v: string) => void;
  file: File | null;
  onFileChange: (f: File | null) => void;
  placeholder: string;
}) {
  const inputRef = useRef<HTMLInputElement>(null);

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    const dropped = e.dataTransfer.files[0];
    if (dropped) onFileChange(dropped);
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <label className="text-sm font-semibold text-gray-700">
          {label} <span className="text-red-500">*</span>
        </label>
        <div className="flex rounded-lg border border-gray-300 overflow-hidden text-xs font-medium">
          <button
            type="button"
            onClick={() => onModeChange('write')}
            className={`px-3 py-1.5 transition-colors ${
              mode === 'write' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'
            }`}
          >
            Write
          </button>
          <button
            type="button"
            onClick={() => onModeChange('upload')}
            className={`px-3 py-1.5 transition-colors ${
              mode === 'upload' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'
            }`}
          >
            Upload
          </button>
        </div>
      </div>

      {mode === 'write' ? (
        <textarea
          value={text}
          onChange={e => onTextChange(e.target.value)}
          placeholder={placeholder}
          rows={8}
          className="w-full p-4 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-sm text-gray-800"
        />
      ) : (
        <div
          onClick={() => inputRef.current?.click()}
          onDrop={handleDrop}
          onDragOver={e => e.preventDefault()}
          className="w-full h-44 border-2 border-dashed border-gray-300 rounded-xl flex flex-col items-center justify-center gap-2 cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-colors"
        >
          <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          {file ? (
            <div className="text-center">
              <p className="text-sm font-medium text-blue-600">{file.name}</p>
              <p className="text-xs text-gray-400 mt-0.5">Click to change</p>
            </div>
          ) : (
            <div className="text-center">
              <p className="text-sm text-gray-500">Drop PDF or DOC/DOCX here</p>
              <p className="text-xs text-gray-400 mt-0.5">or click to browse</p>
            </div>
          )}
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT}
            className="hidden"
            onChange={e => onFileChange(e.target.files?.[0] ?? null)}
          />
        </div>
      )}
    </div>
  );
}

export default function HomePage() {
  const router = useRouter();

  const [jdMode, setJdMode] = useState<'write' | 'upload'>('write');
  const [resumeMode, setResumeMode] = useState<'write' | 'upload'>('write');
  const [jdText, setJdText] = useState('');
  const [resumeText, setResumeText] = useState('');
  const [jdFile, setJdFile] = useState<File | null>(null);
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  function validate(): string {
    if (jdMode === 'write' && !jdText.trim()) return 'Please enter the job description.';
    if (jdMode === 'upload' && !jdFile) return 'Please upload a file for the job description.';
    if (resumeMode === 'write' && !resumeText.trim()) return 'Please enter your resume.';
    if (resumeMode === 'upload' && !resumeFile) return 'Please upload a file for your resume.';
    return '';
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await analyzeWithFiles(
        jdText,
        resumeText,
        jdMode === 'upload' ? jdFile : null,
        resumeMode === 'upload' ? resumeFile : null,
      );
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
          Provide a job description and your resume. Our AI interviewer will assess your real proficiency
          through conversation and generate a personalized learning plan.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6 bg-white p-8 rounded-2xl border border-gray-200 shadow-sm">
        <InputField
          label="Job Description"
          mode={jdMode}
          onModeChange={m => { setJdMode(m); setJdFile(null); }}
          text={jdText}
          onTextChange={setJdText}
          file={jdFile}
          onFileChange={setJdFile}
          placeholder="Paste the full job description here..."
        />

        <InputField
          label="Your Resume"
          mode={resumeMode}
          onModeChange={m => { setResumeMode(m); setResumeFile(null); }}
          text={resumeText}
          onTextChange={setResumeText}
          file={resumeFile}
          onFileChange={setResumeFile}
          placeholder="Paste your resume text here (copy-paste from PDF or Word)..."
        />

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
          { step: '1', title: 'Input', desc: 'Paste or upload JD + Resume' },
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
