import type { Player, SessionRestoreState, SessionState } from './types';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');
const SESSION_ID_KEY = 'prism-cricket-session-id';
const SESSION_BACKUP_KEY = 'prism-cricket-session-backup';

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export function isSessionNotFoundError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404 && /session not found/i.test(error.message);
}

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
    throw new ApiError(message, response.status);
  }
  return response.json() as Promise<T>;
}

function saveSessionSnapshot(state: SessionState): void {
  try {
    localStorage.setItem(SESSION_ID_KEY, state.session_id);
    if (state.restore_state) {
      localStorage.setItem(SESSION_BACKUP_KEY, JSON.stringify(state));
    }
  } catch {
    // The app continues to work for this page view if browser storage is unavailable.
  }
}

function readSavedSession(sessionId: string): SessionState | null {
  try {
    const raw = localStorage.getItem(SESSION_BACKUP_KEY);
    if (!raw) return null;
    const saved = JSON.parse(raw) as SessionState;
    return saved.session_id === sessionId && saved.restore_state?.version === 1 ? saved : null;
  } catch {
    return null;
  }
}

async function withSessionRecovery(
  sessionId: string,
  operation: () => Promise<SessionState>,
): Promise<SessionState> {
  try {
    const state = await operation();
    saveSessionSnapshot(state);
    return state;
  } catch (error) {
    if (!isSessionNotFoundError(error)) throw error;

    const saved = readSavedSession(sessionId);
    if (!saved?.restore_state) throw error;

    // Rebuild the in-memory Python object using the last saved server snapshot,
    // then retry the original operation once. This also handles reset requests.
    const restoreState: SessionRestoreState = saved.restore_state;
    const restored = await request<SessionState>(
      `/api/sessions/${encodeURIComponent(sessionId)}/restore`,
      { method: 'POST', body: JSON.stringify({ restore_state: restoreState }) },
    );
    saveSessionSnapshot(restored);

    const state = await operation();
    saveSessionSnapshot(state);
    return state;
  }
}

export const api = {
  health: () => request<{ status: string }>('/api/health'),
  getPlayers: () => request<Player[]>('/api/players'),
  createSession: async () => {
    const state = await request<SessionState>('/api/sessions', { method: 'POST' });
    saveSessionSnapshot(state);
    return state;
  },
  getSession: (sessionId: string) => withSessionRecovery(
    sessionId,
    () => request<SessionState>(`/api/sessions/${encodeURIComponent(sessionId)}`),
  ),
  generateMatch: (sessionId: string, playerNames: string[]) => withSessionRecovery(
    sessionId,
    () => request<SessionState>(
      `/api/sessions/${encodeURIComponent(sessionId)}/generate-match`,
      { method: 'POST', body: JSON.stringify({ player_names: playerNames }) },
    ),
  ),
  resetSession: (sessionId: string) => withSessionRecovery(
    sessionId,
    () => request<SessionState>(`/api/sessions/${encodeURIComponent(sessionId)}/reset`, { method: 'POST' }),
  ),
};
