import type { Player } from '../types';

type Props = {
  player: Player;
  checked?: boolean;
  selectable?: boolean;
  disabled?: boolean;
  shared?: boolean;
  onCheckedChange?: (name: string, checked: boolean) => void;
};

function roleLabel(player: Player): string {
  if (player.is_batsman && player.is_bowler) return 'ALL-ROUNDER';
  if (player.is_batsman) return 'BATTER';
  if (player.is_bowler) return 'BOWLER';
  return 'FIELD';
}

export default function PlayerCard({
  player, checked = false, selectable = false, disabled = false, shared = false, onCheckedChange,
}: Props) {
  const cardClass = [
    'player-card',
    checked ? 'is-selected' : '',
    shared ? 'is-shared' : '',
    selectable ? 'is-selectable' : '',
  ].filter(Boolean).join(' ');

  const content = (
    <>
      <div className="player-card-top">
        <div className="player-card-identity">
          <span className="player-rank">#{player.rank}</span>
          <span className="player-name">{player.name}</span>
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
        {selectable && (
          <input
            aria-label={`Select ${player.name}`}
            className="player-checkbox"
            type="checkbox"
            checked={checked}
            disabled={disabled}
            onChange={(event) => onCheckedChange?.(player.name, event.currentTarget.checked)}
            onClick={(event) => event.stopPropagation()}
          />
        )}
      </div>
    </>
  );

  if (selectable) {
    return (
      <label className={`${cardClass} player-card-label`}>
        {content}
      </label>
    );
  }
  return <article className={cardClass}>{content}</article>;
}
