const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export async function askQuestion(question, includeRawData = false) {
  const response = await fetch(`${API_BASE_URL}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, include_raw_data: includeRawData }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.error || error.detail || `Request failed (${response.status})`);
  }

  return response.json();
}

export async function healthCheck() {
  const response = await fetch(`${API_BASE_URL}/health`);
  return response.json();
}

export async function getBoardsSummary() {
  const response = await fetch(`${API_BASE_URL}/boards/summary`);
  if (!response.ok) throw new Error('Failed to fetch boards summary');
  return response.json();
}
