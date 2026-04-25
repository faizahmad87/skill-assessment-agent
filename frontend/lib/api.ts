const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function analyzeInput(jdText: string, resumeText: string) {
  const res = await fetch(`${API_URL}/api/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jd_text: jdText, resume_text: resumeText }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Analysis failed');
  }
  return res.json();
}

export async function* sendMessage(sessionId: string, message: string): AsyncGenerator<{ token: string; is_complete: boolean }> {
  const res = await fetch(`${API_URL}/api/assess/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  if (!res.ok) throw new Error('Message failed');

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const text = decoder.decode(value, { stream: true });
    const lines = text.split('\n');
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const parsed = JSON.parse(line.slice(6));
          yield parsed;
        } catch { /* skip malformed */ }
      }
    }
  }
}

export async function getReport(sessionId: string) {
  const res = await fetch(`${API_URL}/api/report/${sessionId}`);
  if (!res.ok) throw new Error('Report not found');
  return res.json();
}

export async function getSessionState(sessionId: string) {
  const res = await fetch(`${API_URL}/api/assess/state/${sessionId}`);
  if (!res.ok) throw new Error('Session not found');
  return res.json();
}
