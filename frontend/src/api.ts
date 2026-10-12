import type { Player, SessionState } from './types';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    });
  } catch {
    throw new Error('Cannot reach the Prism API. Check that FastAPI is running and VITE_API_BASE_URL is correct.');
  }

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json() as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Keep the fallback HTTP message when the response is not JSON.
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>('/api/health'),
  getPlayers: () => request<Player[]>('/api/players'),
  createSession: () => request<SessionState>('/api/sessions', { method: 'POST' }),
  getSession: (sessionId: string) => request<SessionState>(`/api/sessions/${encodeURIComponent(sessionId)}`),
  generateMatch: (sessionId: string, playerNames: string[]) => request<SessionState>(
    `/api/sessions/${encodeURIComponent(sessionId)}/generate-match`,
    { method: 'POST', body: JSON.stringify({ player_names: playerNames }) },
  ),
  resetSession: (sessionId: string) => request<SessionState>(
    `/api/sessions/${encodeURIComponent(sessionId)}/reset`,
    { method: 'POST' },
  ),
};
