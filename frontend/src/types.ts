export interface Player {
  name: string;
  batting: number;
  bowling: number;
  fielding: number;
  is_batsman: boolean;
  is_bowler: boolean;
  strength_score: number;
  rank: number;
}

export interface TeamStats {
  batting: number;
  bowling: number;
  fielding: number;
  strength: number;
  batsmen: number;
  bowlers: number;
  fielders: number;
  elite_batters: number;
  elite_bowlers: number;
  strong_batters: number;
  strong_bowlers: number;
  [key: string]: number;
}

export interface SerializedMatchState {
  team_a: string[];
  team_b: string[];
  shared_player: string | null;
  score: number;
  balance_score: number;
  reshuffle_score: number;
}

export interface SessionRestoreState {
  version: 1;
  match_number: number;
  player_names: string[];
  current_match: SerializedMatchState | null;
  history: SerializedMatchState[];
}

export interface SessionState {
  session_id: string;
  match_number: number;
  players: Player[];
  team_a: Player[];
  team_b: Player[];
  team_a_stats: TeamStats;
  team_b_stats: TeamStats;
  restore_state?: SessionRestoreState;
}
