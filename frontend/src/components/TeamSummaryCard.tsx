import type { TeamStats } from '../types';

type Props = {
  name: 'Team A' | 'Team B';
  stats: TeamStats;
  playerCount: number;
  active: boolean;
  interactive?: boolean;
  onSelect: () => void;
};

function barWidth(value: number, playerCount: number): string {
  const max = Math.max(1, playerCount * 10);
  return `${Math.max(0, Math.min(100, (value / max) * 100))}%`;
}

export default function TeamSummaryCard({ name, stats, playerCount, active, interactive = true, onSelect }: Props) {
  return (
    <button
      type="button"
      className={`team-summary-card ${active && interactive ? 'is-active' : ''} ${!interactive ? 'is-static' : ''}`}
      aria-pressed={interactive ? active : undefined}
      aria-disabled={!interactive}
      disabled={!interactive}
      onClick={onSelect}
    >
      <div className="team-summary-header">
        <div>
          <div className="team-summary-title">{name}</div>
          <div className="team-strength">{Number(stats.strength ?? 0).toFixed(2)}</div>
          <div className="team-muted">TOTAL STRENGTH · {playerCount} PLAYERS</div>
        </div>
        {active && interactive && <span className="active-indicator" aria-label="Players shown">✓</span>}
      </div>

      <div className="mobile-summary-lines">
        <div>Bat <strong>{Number(stats.batting ?? 0).toFixed(2)}</strong> · Elite {stats.elite_batters ?? 0} · Strong {stats.strong_batters ?? 0}</div>
        <div>Bowl <strong>{Number(stats.bowling ?? 0).toFixed(2)}</strong> · Elite {stats.elite_bowlers ?? 0} · Strong {stats.strong_bowlers ?? 0}</div>
        <div>Field <strong>{Number(stats.fielding ?? 0).toFixed(2)}</strong> · Fielder {stats.fielders ?? 0}</div>
      </div>

      <div className="desktop-summary-details">
        <div className="team-skill-row">
          <span>Batting</span><div className="skill-track"><div style={{ width: barWidth(Number(stats.batting ?? 0), playerCount) }} /></div><b>{Number(stats.batting ?? 0).toFixed(2)}</b>
        </div>
        <div className="team-skill-row">
          <span>Bowling</span><div className="skill-track"><div style={{ width: barWidth(Number(stats.bowling ?? 0), playerCount) }} /></div><b>{Number(stats.bowling ?? 0).toFixed(2)}</b>
        </div>
        <div className="team-skill-row">
          <span>Fielding</span><div className="skill-track"><div style={{ width: barWidth(Number(stats.fielding ?? 0), playerCount) }} /></div><b>{Number(stats.fielding ?? 0).toFixed(2)}</b>
        </div>
        <div className="summary-pills">
          <span>Elite batters <b>{stats.elite_batters ?? 0}</b></span>
          <span>Elite bowlers <b>{stats.elite_bowlers ?? 0}</b></span>
          <span>Strong batters <b>{stats.strong_batters ?? 0}</b></span>
          <span>Strong bowlers <b>{stats.strong_bowlers ?? 0}</b></span>
        </div>
      </div>
    </button>
  );
}
