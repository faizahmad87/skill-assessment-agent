'use client';
import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getReport } from '@/lib/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import type { ReportResponse } from '@/lib/types';

const STATUS_COLORS: Record<string, string> = {
  'Strong': '#16a34a',
  'Adequate': '#2563eb',
  'Gap': '#d97706',
  'Critical Gap': '#dc2626',
};

export default function ReportPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    getReport(sessionId)
      .then(setReport)
      .catch(() => setError('Failed to load report. Please try again.'))
      .finally(() => setLoading(false));
  }, [sessionId]);

  if (loading) return (
    <div className="flex flex-col items-center justify-center h-screen gap-3">
      <svg className="animate-spin h-8 w-8 text-blue-600" viewBox="0 0 24 24" fill="none">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
      </svg>
      <p className="text-gray-500 text-sm">Generating your personalized report...</p>
    </div>
  );

  if (error || !report) return (
    <div className="flex flex-col items-center justify-center h-screen gap-3">
      <p className="text-red-500">{error || 'Report not found.'}</p>
      <button onClick={() => router.push('/')} className="text-blue-600 hover:underline text-sm">Start new assessment</button>
    </div>
  );

  const readinessColor = report.readiness_label === 'Ready' ? 'text-green-600'
    : report.readiness_label === 'Partially Ready' ? 'text-yellow-600'
    : 'text-red-600';

  return (
    <main className="max-w-4xl mx-auto px-4 py-10 space-y-8">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Your Skill Assessment Report</h1>
        <p className="text-gray-500">Here is your personalized skill analysis and learning plan.</p>
      </div>

      {/* Overview */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white p-6 rounded-2xl border border-gray-200 text-center shadow-sm">
          <div className="text-4xl font-bold text-blue-600">{report.overall_score}%</div>
          <div className="text-xs text-gray-500 mt-1 font-medium uppercase tracking-wide">Overall Readiness</div>
        </div>
        <div className="bg-white p-6 rounded-2xl border border-gray-200 text-center shadow-sm">
          <div className={`text-2xl font-bold ${readinessColor}`}>{report.readiness_label}</div>
          <div className="text-xs text-gray-500 mt-1 font-medium uppercase tracking-wide">Status</div>
        </div>
        <div className="bg-white p-6 rounded-2xl border border-gray-200 text-center shadow-sm">
          <div className="text-4xl font-bold text-orange-500">{report.weeks_to_ready}w</div>
          <div className="text-xs text-gray-500 mt-1 font-medium uppercase tracking-wide">Weeks to Job-Ready</div>
        </div>
      </div>

      {/* Chart */}
      <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 mb-5">Skill Scores</h2>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={report.skill_scores} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="skill" tick={{ fontSize: 11 }} />
            <YAxis domain={[0, 10]} tick={{ fontSize: 11 }} />
            <Tooltip formatter={(val) => [typeof val === 'number' ? `${val.toFixed(1)}/10` : val, 'Score']} />
            <Bar dataKey="score" radius={[4, 4, 0, 0]}>
              {report.skill_scores.map((entry, i) => (
                <Cell key={i} fill={STATUS_COLORS[entry.status_label] || '#6b7280'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div className="flex gap-4 mt-3 justify-center flex-wrap">
          {Object.entries(STATUS_COLORS).map(([label, color]) => (
            <div key={label} className="flex items-center gap-1.5 text-xs text-gray-500">
              <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: color }} />
              {label}
            </div>
          ))}
        </div>
      </div>

      {/* Skill Table */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
        <h2 className="text-lg font-semibold text-gray-900 px-6 pt-6 pb-3">Skill Breakdown</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Skill</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Score</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Status</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {report.skill_scores.map(skill => (
                <tr key={skill.skill} className="hover:bg-gray-50">
                  <td className="px-6 py-4 font-medium text-gray-900">{skill.skill}</td>
                  <td className="px-6 py-4 text-gray-700">{skill.score.toFixed(1)}/10</td>
                  <td className="px-6 py-4">
                    <span className="px-2.5 py-1 rounded-full text-xs font-semibold" style={{
                      backgroundColor: (STATUS_COLORS[skill.status_label] || '#6b7280') + '18',
                      color: STATUS_COLORS[skill.status_label] || '#6b7280'
                    }}>
                      {skill.status_label}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-gray-500 text-xs max-w-xs">{skill.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Learning Plan */}
      {report.learning_plan.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Personalized Learning Plan</h2>
          <div className="space-y-3">
            {report.learning_plan.map(item => (
              <details key={item.skill} className="bg-white rounded-2xl border border-gray-200 shadow-sm group">
                <summary className="p-5 cursor-pointer list-none flex justify-between items-center hover:bg-gray-50 rounded-2xl">
                  <div className="flex items-center gap-3">
                    <span className="w-6 h-6 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0">
                      {item.priority}
                    </span>
                    <span className="font-semibold text-gray-900">{item.skill}</span>
                    <span className="px-2 py-0.5 rounded text-xs font-medium" style={{
                      backgroundColor: (STATUS_COLORS[item.gap_size] || '#6b7280') + '18',
                      color: STATUS_COLORS[item.gap_size] || '#6b7280'
                    }}>
                      {item.gap_size}
                    </span>
                  </div>
                  <span className="text-sm text-gray-400 flex-shrink-0">{item.estimated_hours}h</span>
                </summary>
                <div className="px-5 pb-5 space-y-4 border-t border-gray-100 pt-4">
                  <div>
                    <h4 className="text-sm font-semibold text-gray-700 mb-2">Free Resources</h4>
                    <ul className="space-y-1.5">
                      {item.resources?.map((r, i) => (
                        <li key={i} className="flex items-center gap-2 text-sm">
                          <span className="text-xs px-1.5 py-0.5 bg-green-100 text-green-700 rounded font-medium flex-shrink-0">{r.type}</span>
                          <a href={r.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline truncate">
                            {r.title}
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-700 mb-1">Project Idea</h4>
                    <p className="text-sm text-gray-600">{item.project_idea}</p>
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-700 mb-1">Study Plan</h4>
                    <p className="text-sm text-gray-600">{item.weekly_plan}</p>
                  </div>
                </div>
              </details>
            ))}
          </div>
        </div>
      )}

      <div className="text-center pb-8">
        <button onClick={() => router.push('/')} className="text-sm text-gray-400 hover:text-gray-600 hover:underline">
          Start a new assessment
        </button>
      </div>
    </main>
  );
}
