import { useEffect, useMemo, useState } from 'react';
import { api, isSessionNotFoundError } from './api';
import PlayerCard from './components/PlayerCard';
import TeamSummaryCard from './components/TeamSummaryCard';
import type { Player, SessionState } from './types';

const SESSION_STORAGE_KEY = 'prism-cricket-session-id';
const UI_STATE_STORAGE_KEY = 'prism-cricket-ui-state';

type Screen = 'select' | 'teams';
type ActiveTeam = 'A' | 'B';

type PersistedUiState = {
  session_id: string;
  selected_names: string[];
  screen: Screen;
  search: string;
  active_team: ActiveTeam;
};

// Team assignment in a generated match. Shared players appear in both teams.
type TeamAssignment = 'A' | 'B' | 'SHARED';

function assignmentMap(teamA: string[], teamB: string[]): Map<string, TeamAssignment> {
  const namesA = new Set(teamA);
  const namesB = new Set(teamB);
  const assignments = new Map<string, TeamAssignment>();

  for (const name of namesA) {
    assignments.set(name, namesB.has(name) ? 'SHARED' : 'A');
  }
  for (const name of namesB) {
    if (!assignments.has(name)) assignments.set(name, 'B');
  }

  return assignments;
}

function readPersistedUiState(): PersistedUiState | null {
  try {
    const raw = localStorage.getItem(UI_STATE_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as PersistedUiState;
    if (
      typeof parsed.session_id !== 'string' ||
      !Array.isArray(parsed.selected_names) ||
      !['select', 'teams'].includes(parsed.screen) ||
      typeof parsed.search !== 'string' ||
      !['A', 'B'].includes(parsed.active_team)
    ) return null;
    return parsed;
  } catch {
    return null;
  }
}

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
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const [teamSummariesInteractive, setTeamSummariesInteractive] = useState(() =>
    typeof window !== 'undefined' && window.matchMedia('(max-width: 760px) and (orientation: portrait)').matches
  );

  // Team summaries act as team selectors only on portrait mobile.
  // Desktop and mobile landscape display both line-ups together, so summaries are informational.
  useEffect(() => {
    const query = window.matchMedia('(max-width: 760px) and (orientation: portrait)');
    const update = () => setTeamSummariesInteractive(query.matches);
    update();
    query.addEventListener('change', update);
    return () => query.removeEventListener('change', update);
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function boot() {
      try {
        const allPlayers = await api.getPlayers();
        if (cancelled) return;
        setPlayers(allPlayers);

        const savedUi = readPersistedUiState();
        const existingId = localStorage.getItem(SESSION_STORAGE_KEY) || savedUi?.session_id || null;
        let current: SessionState;
        if (existingId) {
          try {
            current = await api.getSession(existingId);
          } catch (error) {
            if (!isSessionNotFoundError(error)) throw error;
            // No restorable snapshot exists (for example, a session from before
            // browser snapshots were introduced), so start a new blank session.
            current = await api.createSession();
          }
        } else {
          current = await api.createSession();
        }
        if (cancelled) return;

        const savedUiForSession = savedUi?.session_id === current.session_id ? savedUi : null;
        const validNames = new Set(allPlayers.map((player) => player.name));
        const rememberedNames = savedUiForSession
          ? savedUiForSession.selected_names.filter((name) => validNames.has(name))
          : current.players.map((player) => player.name);
        const rememberedScreen: Screen =
          current.match_number > 0 && savedUiForSession?.screen === 'select'
            ? 'select'
            : current.match_number > 0 ? 'teams' : 'select';

        setSession(current);
        setScreen(rememberedScreen);
        setSelectedNames(new Set(rememberedNames));
        setSearch(savedUiForSession?.search ?? '');
        setActiveTeam(savedUiForSession?.active_team ?? 'A');
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Could not load Prism.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void boot();
    return () => { cancelled = true; };
  }, []);

  // Keep the current browser view (including unsubmitted player edits) durable
  // across refreshes. The API module separately stores the restorable Python state.
  useEffect(() => {
    if (!session) return;
    const persisted: PersistedUiState = {
      session_id: session.session_id,
      selected_names: [...selectedNames],
      screen,
      search,
      active_team: activeTeam,
    };
    try {
      localStorage.setItem(SESSION_STORAGE_KEY, session.session_id);
      localStorage.setItem(UI_STATE_STORAGE_KEY, JSON.stringify(persisted));
    } catch {
      // Ignore unavailable or full browser storage; the current page remains usable.
    }
  }, [session, selectedNames, screen, search, activeTeam]);

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

  // Compare each player with their assignment in the immediately previous match.
  // A player absent from the previous match is a new addition and gets no label.
  // Match 1 intentionally has no movement indicators.
  const movementByName = useMemo(() => {
    const movements = new Map<string, string>();
    if (!session || session.match_number <= 1) return movements;

    const history = session.restore_state?.history ?? [];
    if (history.length < 2) return movements;

    const previousMatch = history[history.length - 2];
    const previousAssignment = assignmentMap(previousMatch.team_a, previousMatch.team_b);
    const currentAssignment = assignmentMap(
      teamA.map((player) => player.name),
      teamB.map((player) => player.name),
    );

    for (const [name, currentTeam] of currentAssignment) {
      const previousTeam = previousAssignment.get(name);
      if (previousTeam && previousTeam !== currentTeam) {
        movements.set(name, `${previousTeam} → ${currentTeam}`);
      }
    }

    return movements;
  }, [session, teamA, teamB]);

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

  function clearOrReset() {
    if (!session) return;
    setShowResetConfirm(true);
  }

  async function confirmReset() {
    if (!session) return;
    setBusy(true);
    setError('');
    try {
      const reset = await api.resetSession(session.session_id);
      setSession(reset);
      setSelectedNames(new Set());
      setSearch('');
      setScreen('select');
      setActiveTeam('A');
      setShowResetConfirm(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not reset the session.');
      setShowResetConfirm(false);
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return <main className="page-shell"><div className="loading-panel">Loading Prism Team Balancer…</div></main>;
  }

  if (error && !session) {
    return <main className="page-shell"><div className="error-panel"><h1>Prism Team Balancer could not connect</h1><p>{error}</p><p>Check that the FastAPI server is running and the API URL is configured.</p></div></main>;
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
            <div className="selection-heading-actions">
              <span className="selection-counter"><strong>{selectedNames.size}</strong><span> selected</span></span>
              <button type="button" className="button button-quiet reset-session-inline" onClick={clearOrReset} disabled={busy}>Reset Session</button>
            </div>
          </div>
          <div className="selection-toolbar">
            <label className="search-box">
              <span aria-hidden="true">⌕</span>
              <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search player name…" aria-label="Search players by name" />
              {search && <button type="button" className="clear-search" onClick={() => setSearch('')} aria-label="Clear search">×</button>}
            </label>
            <div className={`toolbar-actions ${session?.match_number ? 'is-editing' : 'is-initial'}`}>
              <button type="button" className="button button-secondary" onClick={() => setSelectedNames(new Set())} disabled={selectedNames.size === 0}>Clear Selection</button>
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
            <div>
              <h2 id="teams-heading">Generated Teams</h2>
              <p>
                <span className="mobile-team-select-hint">Tap a team summary to view its players on mobile.</span>
                <span className="teams-comparison-hint">Compare both teams and their player strengths side by side.</span>
              </p>
            </div>
            <div className="match-badge">MATCH {session.match_number}</div>
          </div>
          <div className="team-summary-grid">
            <TeamSummaryCard name="Team A" stats={session.team_a_stats} playerCount={teamA.length} active={activeTeam === 'A'} interactive={teamSummariesInteractive} onSelect={() => setActiveTeam('A')} />
            <TeamSummaryCard name="Team B" stats={session.team_b_stats} playerCount={teamB.length} active={activeTeam === 'B'} interactive={teamSummariesInteractive} onSelect={() => setActiveTeam('B')} />
          </div>
          <details className="balance-explainer">
            <summary className="balance-explainer-toggle">
              <div className="balance-explainer-intro">
                <div className="balance-explainer-kicker">BEST-BALANCED PAIRING</div>
                <h3 id="balance-explainer-heading">How the algorithm chose these teams</h3>
                <p className="balance-explainer-summary-hint">See what goes into balancing the two sides.</p>
              </div>
              <span className="balance-explainer-chevron" aria-hidden="true" />
            </summary>
            <div className="balance-explainer-content" aria-labelledby="balance-explainer-heading">
              <div className="balance-explainer-intro balance-explainer-detail-intro">
                <p>Team A and Team B above were selected together as the most balanced matchup the algorithm found for the players chosen. The aim is to make the two sides competitive with each other, not to label one team as stronger.</p>
              </div>
              <div className="balance-principles-grid">
                <div className="balance-principle">
                  <span className="balance-principle-number" aria-hidden="true">01</span>
                  <div><h4>Skills across both teams</h4><p>The algorithm compares batting, bowling, fielding and overall player strength, aiming to spread strengths across both sides.</p></div>
                </div>
                <div className="balance-principle">
                  <span className="balance-principle-number" aria-hidden="true">02</span>
                  <div><h4>Roles and coverage</h4><p>It considers the mix of batters, bowlers and field-only players so one side does not get an obvious role advantage.</p></div>
                </div>
                <div className="balance-principle">
                  <span className="balance-principle-number" aria-hidden="true">03</span>
                  <div><h4>Impact players</h4><p>It also considers how highly rated, strong and lower-rated batting and bowling skills are distributed between the teams.</p></div>
                </div>
                <div className="balance-principle">
                  <span className="balance-principle-number" aria-hidden="true">04</span>
                  <div><h4>Continuity between matches</h4><p>{session.match_number > 1 ? 'For later matches, the algorithm also prefers to avoid unnecessary switches between Team A and Team B while keeping the teams balanced.' : 'From Match 2 onward, the algorithm also considers previous assignments and prefers to avoid unnecessary switches between teams.'}</p></div>
                </div>
              </div>
              <p className="balance-explainer-footnote">The algorithm compares valid ways to split the selected group and chooses the pairing that best fits these priorities. It is a guide to fairer teams—not a prediction of the match result.</p>
            </div>
          </details>
          <div className="team-player-panels">
            {([
              { key: 'A', name: 'Team A', team: teamA },
              { key: 'B', name: 'Team B', team: teamB },
            ] as const).map(({ key, name, team }) => (
              <section key={key} className={`team-player-panel ${activeTeam === key ? 'is-active' : ''}`} aria-label={`${name} players`}>
                <h3>{name} Players <span>{team.length}</span></h3>
                <div className="team-player-list">
                  {sortTeam(team).map((player) => (
                    <PlayerCard
                      key={`${key}-${player.name}`}
                      player={player}
                      shared={sharedNames.has(player.name)}
                      movement={movementByName.get(player.name)}
                    />
                  ))}
                </div>
              </section>
            ))}
          </div>
          <div className="team-actions">
            <button type="button" className="button button-secondary" onClick={editPlayers}>Edit Players</button>
            <button type="button" className="button button-quiet" onClick={clearOrReset} disabled={busy}>Reset Session</button>
          </div>
        </section>
      )}
      <footer className="app-footer"><span>PRISM · BUILT FOR SUNDAY CRICKET</span><span>Responsive by design</span></footer>

      {showResetConfirm && (
        <div
          className="dialog-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget && !busy) setShowResetConfirm(false);
          }}
          onKeyDown={(event) => {
            if (event.key === 'Escape' && !busy) setShowResetConfirm(false);
          }}
        >
          <section className="reset-dialog" role="dialog" aria-modal="true" aria-labelledby="reset-dialog-title">
            <div className="dialog-accent" aria-hidden="true"><span>↺</span></div>
            <h2 id="reset-dialog-title">Reset Session?</h2>
            <div className="dialog-actions">
              <button type="button" className="button button-secondary" onClick={() => setShowResetConfirm(false)} disabled={busy} autoFocus>Cancel</button>
              <button type="button" className="button button-primary" onClick={() => void confirmReset()} disabled={busy}>
                {busy ? 'Resetting…' : 'Reset'}
              </button>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}
