import { useEffect, useMemo, useState } from 'react';
import { api } from './api';
import PlayerCard from './components/PlayerCard';
import TeamSummaryCard from './components/TeamSummaryCard';
import type { Player, SessionState } from './types';

const SESSION_STORAGE_KEY = 'prism-cricket-session-id';

type Screen = 'select' | 'teams';

export default function App() {
  const [players, setPlayers] = useState<Player[]>([]);
  const [session, setSession] = useState<SessionState | null>(null);
  const [selectedNames, setSelectedNames] = useState<Set<string>>(new Set());
  const [search, setSearch] = useState('');
  const [screen, setScreen] = useState<Screen>('select');
  const [activeTeam, setActiveTeam] = useState<'A' | 'B'>('A');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    async function boot() {
      try {
        const allPlayers = await api.getPlayers();
        if (cancelled) return;
        setPlayers(allPlayers);

        const existingId = localStorage.getItem(SESSION_STORAGE_KEY);
        let current: SessionState;
        if (existingId) {
          try {
            current = await api.getSession(existingId);
          } catch {
            current = await api.createSession();
          }
        } else {
          current = await api.createSession();
        }
        if (cancelled) return;
        localStorage.setItem(SESSION_STORAGE_KEY, current.session_id);
        setSession(current);
        setScreen(current.match_number > 0 ? 'teams' : 'select');
        setSelectedNames(new Set(current.players.map((player) => player.name)));
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Could not load Prism.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void boot();
    return () => { cancelled = true; };
  }, []);

  const filteredPlayers = useMemo(() => {
    const prefix = search.trim().toLocaleLowerCase();
    if (!prefix) return players;
    return players.filter((player) => player.name.toLocaleLowerCase().startsWith(prefix));
  }, [players, search]);

  const teamA = session?.team_a ?? [];
  const teamB = session?.team_b ?? [];
  const sharedNames = useMemo(() => {
    const bNames = new Set(teamB.map((player) => player.name));
    return new Set(teamA.filter((player) => bNames.has(player.name)).map((player) => player.name));
  }, [teamA, teamB]);

  function updateSelection(name: string, checked: boolean) {
    setSelectedNames((previous) => {
      const next = new Set(previous);
      if (checked) next.add(name);
      else next.delete(name);
      return next;
    });
  }

  function sortTeam(team: Player[]) {
    return [...team].sort((a, b) => {
      const aShared = sharedNames.has(a.name) ? 1 : 0;
      const bShared = sharedNames.has(b.name) ? 1 : 0;
      if (aShared !== bShared) return bShared - aShared;
      return b.strength_score - a.strength_score || a.name.localeCompare(b.name);
    });
  }

  async function generate() {
    if (!session || selectedNames.size < 2) return;
    setBusy(true);
    setError('');
    try {
      const updated = await api.generateMatch(session.session_id, players.filter((p) => selectedNames.has(p.name)).map((p) => p.name));
      setSession(updated);
      setSelectedNames(new Set(updated.players.map((player) => player.name)));
      setActiveTeam('A');
      setScreen('teams');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not generate teams.');
    } finally {
      setBusy(false);
    }
  }

  function editPlayers() {
    if (session) setSelectedNames(new Set(session.players.map((player) => player.name)));
    setSearch('');
    setScreen('select');
  }

  async function clearOrReset() {
    if (!session) return;
    if (session.match_number > 0 && !window.confirm('Reset this cricket session and start again?')) return;
    setBusy(true);
    setError('');
    try {
      const reset = await api.resetSession(session.session_id);
      setSession(reset);
      setSelectedNames(new Set());
      setSearch('');
      setScreen('select');
      setActiveTeam('A');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not reset the session.');
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return <main className="page-shell"><div className="loading-panel">Loading Prism…</div></main>;
  }

  if (error && !session) {
    return <main className="page-shell"><div className="error-panel"><h1>Prism could not connect</h1><p>{error}</p><p>Check that the FastAPI server is running and the API URL is configured.</p></div></main>;
  }

  return (
    <main className="page-shell">
      <header className="app-header">
        <div className="eyebrow">SUNDAY CRICKET · TEAM BUILDER</div>
        <h1>Prism <span>Team Balancer</span></h1>
        <p className="page-subtitle">Fair teams. Less debate. More cricket.</p>
      </header>

      {error && <div className="inline-error" role="alert">{error}</div>}

      {screen === 'select' && (
        <section aria-labelledby="select-heading">
          <div className="section-heading-row">
            <div><h2 id="select-heading">{session?.match_number ? 'Edit Players' : 'Select Players'}</h2><p>Choose the players available for this match.</p></div>
            <span className="selection-counter"><strong>{selectedNames.size}</strong><span> selected</span></span>
          </div>
          <div className="selection-toolbar">
            <label className="search-box">
              <span aria-hidden="true">⌕</span>
              <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search player name…" aria-label="Search players by name" />
              {search && <button type="button" className="clear-search" onClick={() => setSearch('')} aria-label="Clear search">×</button>}
            </label>
            <div className="toolbar-actions">
              <button type="button" className="button button-secondary" onClick={() => setSelectedNames(new Set())} disabled={selectedNames.size === 0}>Clear selection</button>
              {session?.match_number ? <button type="button" className="button button-secondary" onClick={() => setScreen('teams')}>Cancel</button> : null}
              <button type="button" className="button button-primary" onClick={() => void generate()} disabled={selectedNames.size < 2 || busy}>
                {busy ? 'Generating…' : session?.match_number ? 'Generate Next Match' : 'Generate Teams'}
              </button>
            </div>
          </div>
          <div className="player-grid">
            {filteredPlayers.map((player) => (
              <PlayerCard key={player.name} player={player} selectable checked={selectedNames.has(player.name)} onCheckedChange={updateSelection} />
            ))}
            {filteredPlayers.length === 0 && <div className="empty-state">No players found beginning with “{search}”.</div>}
          </div>
        </section>
      )}

      {screen === 'teams' && session && session.match_number > 0 && (
        <section aria-labelledby="teams-heading" className="teams-section">
          <div className="section-heading-row team-title-row">
            <div><h2 id="teams-heading">Generated Teams</h2><p>Tap a team summary to view its players on mobile.</p></div>
            <div className="match-badge">MATCH {session.match_number}</div>
          </div>
          <div className="team-summary-grid">
            <TeamSummaryCard name="Team A" stats={session.team_a_stats} playerCount={teamA.length} active={activeTeam === 'A'} onSelect={() => setActiveTeam('A')} />
            <TeamSummaryCard name="Team B" stats={session.team_b_stats} playerCount={teamB.length} active={activeTeam === 'B'} onSelect={() => setActiveTeam('B')} />
          </div>
          <div className="team-player-panels">
            {([
              { key: 'A', name: 'Team A', team: teamA },
              { key: 'B', name: 'Team B', team: teamB },
            ] as const).map(({ key, name, team }) => (
              <section key={key} className={`team-player-panel ${activeTeam === key ? 'is-active' : ''}`} aria-label={`${name} players`}>
                <h3>{name} Players <span>{team.length}</span></h3>
                <div className="team-player-list">
                  {sortTeam(team).map((player) => (
                    <PlayerCard key={`${key}-${player.name}`} player={player} shared={sharedNames.has(player.name)} />
                  ))}
                </div>
              </section>
            ))}
          </div>
          <div className="team-actions">
            <button type="button" className="button button-secondary" onClick={editPlayers}>Edit Players</button>
            <button type="button" className="button button-primary" onClick={() => void generate()} disabled={busy || selectedNames.size < 2}>
              {busy ? 'Generating…' : 'Generate Next Match'}
            </button>
            <button type="button" className="button button-quiet" onClick={() => void clearOrReset()} disabled={busy}>Reset Session</button>
          </div>
        </section>
      )}
      <footer className="app-footer"><span>PRISM · BUILT FOR SUNDAY CRICKET</span><span>Responsive by design</span></footer>
    </main>
  );
}
