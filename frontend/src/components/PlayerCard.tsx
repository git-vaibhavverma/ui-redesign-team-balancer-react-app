import type { Player } from '../types';

type Props = {
  player: Player;
  checked?: boolean;
  selectable?: boolean;
  disabled?: boolean;
  shared?: boolean;
  movement?: string;
  compact?: boolean;
  onCheckedChange?: (name: string, checked: boolean) => void;
};

function roleLabel(player: Player): string {
  if (player.is_batsman && player.is_bowler) return 'ALL-ROUNDER';
  if (player.is_batsman) return 'BATTER';
  if (player.is_bowler) return 'BOWLER';
  return 'FIELD';
}

export default function PlayerCard({
  player,
  checked = false,
  selectable = false,
  disabled = false,
  shared = false,
  movement,
  compact = false,
  onCheckedChange,
}: Props) {
  const cardClass = [
    'player-card',
    checked ? 'is-selected' : '',
    shared ? 'is-shared' : '',
    selectable ? 'is-selectable' : '',
    compact && !selectable ? 'is-compact' : '',
  ].filter(Boolean).join(' ');

  const content = compact && !selectable ? (
    <div className="compact-player-card-content">
      <div className="compact-player-card-top">
        <div className="compact-player-card-identity">
          <span className="player-rank">#{player.rank}</span>
          <span className="player-name">{player.name}</span>
        </div>
        <div className="player-strength">{player.strength_score.toFixed(2)}</div>
      </div>
      <div className="compact-player-card-bottom">
        <span className="player-role">{roleLabel(player)}</span>
        {shared && <span className="shared-tag">SHARED</span>}
      </div>
    </div>
  ) : (
    <>
      <div className="player-card-top">
        <div className="player-card-identity">
          <span className="player-rank">#{player.rank}</span>
          <span className="player-name">{player.name}</span>
          {movement && <span className="player-movement" aria-label={`Player movement: ${movement}`}>{movement}</span>}
          {shared && <span className="shared-tag">SHARED</span>}
        </div>
        <div className="player-strength">{player.strength_score.toFixed(2)}</div>
      </div>
      <div className="player-role">{roleLabel(player)}</div>
      <div className="player-card-bottom">
        <div className="player-skills">
          <span>BAT <b>{player.batting.toFixed(2)}</b></span>
          <span>BOWL <b>{player.bowling.toFixed(2)}</b></span>
          <span>FIELD <b>{player.fielding.toFixed(2)}</b></span>
        </div>
      </div>
    </>
  );

  if (selectable) {
    return (
      <button
        type="button"
        className={`${cardClass} player-card-button`}
        aria-pressed={checked}
        aria-label={`${player.name}${checked ? ', selected' : ', not selected'}`}
        disabled={disabled}
        onClick={() => onCheckedChange?.(player.name, !checked)}
      >
        {content}
      </button>
    );
  }

  return <article className={cardClass}>{content}</article>;
}
