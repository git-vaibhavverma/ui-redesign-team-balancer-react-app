# ============================================================
# TEAM BALANCING ENGINE
# ============================================================
#
# This is the core business logic of the application.
#
# Given:
#
#   - current players
#   - previous team assignments
#
# the engine evaluates possible team combinations and chooses
# the combination with the lowest total score.
#
# LOWER SCORE = BETTER
#
# The total score consists of:
#
#   1. Team balance score
#   2. Reshuffle penalty
#
# The algorithm deliberately evaluates all possible meaningful
# combinations because the Sunday group is relatively small
# (typically around 10-25 players).
# ============================================================

import numpy as np
from numba import njit

from config import (
    SKILL_WEIGHTS,
    ROLE_PENALTIES,
    OVERALL_STRENGTH_PENALTY,
    IMPACT_THRESHOLDS,
    ELITE_PLAYER_PENALTY,
    STRONG_PLAYER_PENALTY,
    WEAK_PLAYER_PENALTY,
    RESHUFFLE_PENALTY,
)


# ============================================================
# PLAYER STRENGTH
# ============================================================

def player_strength(player):
    """
    Calculate the weighted overall strength of a player.

    Example:

        batting  = 8.50
        bowling  = 9.00
        fielding = 8.00

    Using the current weights:

        8.50 * 0.35
      + 9.00 * 0.45
      + 8.00 * 0.20

    The returned value is deliberately NOT rounded.

    Why?

    The optimizer should retain full floating-point precision
    internally. We only format values to two decimal places
    when displaying them to the user.
    """

    return (
        player["batting"]
        * SKILL_WEIGHTS["batting"]

        + player["bowling"]
        * SKILL_WEIGHTS["bowling"]

        + player["fielding"]
        * SKILL_WEIGHTS["fielding"]
    )


# ============================================================
# IMPACT TIER HELPERS
# ============================================================

def is_elite_batter(player):
    """
    Return True when the player's batting rating is Elite.

    Elite = 9.00 or above.
    """

    return (
        player["batting"]
        >= IMPACT_THRESHOLDS["elite"]
    )


def is_elite_bowler(player):
    """
    Return True when the player's bowling rating is Elite.
    """

    return (
        player["bowling"]
        >= IMPACT_THRESHOLDS["elite"]
    )


def is_strong_batter(player):
    """
    Return True when the player's batting rating is Strong.

    IMPORTANT:
    Elite players are deliberately excluded.

    Therefore:

        9.35 -> Elite
        8.75 -> Strong
        7.95 -> Normal
    """

    return (
        IMPACT_THRESHOLDS["strong"]
        <= player["batting"]
        < IMPACT_THRESHOLDS["elite"]
    )


def is_strong_bowler(player):
    """
    Return True when the player's bowling rating is Strong.

    Again, Elite players are excluded.
    """

    return (
        IMPACT_THRESHOLDS["strong"]
        <= player["bowling"]
        < IMPACT_THRESHOLDS["elite"]
    )


def is_weak_batter(player):
    """
    Return True when the player's batting rating is Weak.
    """

    return (
        player["batting"]
        <= IMPACT_THRESHOLDS["weak"]
    )


def is_weak_bowler(player):
    """
    Return True when the player's bowling rating is Weak.
    """

    return (
        player["bowling"]
        <= IMPACT_THRESHOLDS["weak"]
    )


# ============================================================
# TEAM STATISTICS
# ============================================================

def team_stats(team):
    """
    Calculate all statistics needed to evaluate a team.

    These totals retain floating-point precision.

    The UI is responsible for displaying them as, for example:

        52.37
        48.92
        54.11

    rather than rounding the values here.
    """

    # --------------------------------------------------------
    # Raw skill totals
    # --------------------------------------------------------

    batting_total = sum(
        p["batting"]
        for p in team
    )

    bowling_total = sum(
        p["bowling"]
        for p in team
    )

    fielding_total = sum(
        p["fielding"]
        for p in team
    )

    # --------------------------------------------------------
    # Weighted overall strength
    # --------------------------------------------------------

    strength_total = sum(
        player_strength(p)
        for p in team
    )

    # --------------------------------------------------------
    # Player roles
    # --------------------------------------------------------

    batsmen = sum(
        1
        for p in team
        if p["is_batsman"]
    )

    bowlers = sum(
        1
        for p in team
        if p["is_bowler"]
    )

    # added by VV
    fielders = sum(
            1
            for p in team
            if not p["is_bowler"] and not p["is_batsman"]
        )
    
    # --------------------------------------------------------
    # Elite players
    # --------------------------------------------------------

    elite_batters = sum(
        1
        for p in team
        if is_elite_batter(p)
    )

    elite_bowlers = sum(
        1
        for p in team
        if is_elite_bowler(p)
    )

    # --------------------------------------------------------
    # Strong players
    #
    # Because the helper functions exclude Elite players,
    # these counts represent only the 8.00-8.99 range.
    # --------------------------------------------------------

    strong_batters = sum(
        1
        for p in team
        if is_strong_batter(p)
    )

    strong_bowlers = sum(
        1
        for p in team
        if is_strong_bowler(p)
    )

    # --------------------------------------------------------
    # Weak players
    # --------------------------------------------------------

    weak_batters = sum(
        1
        for p in team
        if is_weak_batter(p)
    )

    weak_bowlers = sum(
        1
        for p in team
        if is_weak_bowler(p)
    )

    return {
        "batting": batting_total,
        "bowling": bowling_total,
        "fielding": fielding_total,
        "strength": strength_total,

        "batsmen": batsmen,
        "bowlers": bowlers,
        "fielders": fielders, # added by VV

        "elite_batters": elite_batters,
        "elite_bowlers": elite_bowlers,

        "strong_batters": strong_batters,
        "strong_bowlers": strong_bowlers,

        "weak_batters": weak_batters,
        "weak_bowlers": weak_bowlers,
    }


# ============================================================
# NORMALIZED DIFFERENCE
# ============================================================

def normalized_difference(value_a, value_b):
    """
    Calculate the relative difference between two values.

    Formula:

        abs(A - B) / (A + B)

    This is useful because the difference becomes relative to
    the size of the underlying values.

    Example:

        Team A batting = 50
        Team B batting = 52

        difference = 2 / 102

    rather than simply using "2".
    """

    total = value_a + value_b

    # Avoid division by zero.
    if total == 0:
        return 0

    return (
        abs(value_a - value_b)
        / total
    )


# ============================================================
# BASE BALANCE SCORE
# ============================================================

def base_balance_score(team_a, team_b):
    """
    Calculate the score representing how well balanced the two
    teams are.

    LOWER SCORE = BETTER BALANCE.

    This score does NOT consider reshuffling.

    Reshuffling is handled separately by reshuffle_score().
    """

    stats_a = team_stats(team_a)
    stats_b = team_stats(team_b)

    score = 0

    # --------------------------------------------------------
    # 1. Batting balance
    # --------------------------------------------------------

    score += (
        normalized_difference(
            stats_a["batting"],
            stats_b["batting"],
        )
        * SKILL_WEIGHTS["batting"]
    )

    # --------------------------------------------------------
    # 2. Bowling balance
    # --------------------------------------------------------

    score += (
        normalized_difference(
            stats_a["bowling"],
            stats_b["bowling"],
        )
        * SKILL_WEIGHTS["bowling"]
    )

    # --------------------------------------------------------
    # 3. Fielding balance
    # --------------------------------------------------------

    score += (
        normalized_difference(
            stats_a["fielding"],
            stats_b["fielding"],
        )
        * SKILL_WEIGHTS["fielding"]
    )

    # --------------------------------------------------------
    # 4. Number of batsmen
    # --------------------------------------------------------

    score += (
        normalized_difference(
            stats_a["batsmen"],
            stats_b["batsmen"],
        )
        * ROLE_PENALTIES["batsmen"]
    )

    # --------------------------------------------------------
    # 5. Number of bowlers
    # --------------------------------------------------------

    score += (
        normalized_difference(
            stats_a["bowlers"],
            stats_b["bowlers"],
        )
        * ROLE_PENALTIES["bowlers"]
    )

    # Added by VV
    # --------------------------------------------------------
    # 5. Number of fielders
    # --------------------------------------------------------

    score += (
        normalized_difference(
            stats_a["fielders"],
            stats_b["fielders"],
        )
        * ROLE_PENALTIES["fielders"]
    )

    # --------------------------------------------------------
    # 6. Overall weighted strength
    # --------------------------------------------------------

    score += (
        normalized_difference(
            stats_a["strength"],
            stats_b["strength"],
        )
        * OVERALL_STRENGTH_PENALTY
    )

    # --------------------------------------------------------
    # 7. Elite batting impact
    # --------------------------------------------------------
    #
    # This prevents a team from accidentally collecting most
    # of the highest-rated batters even if the overall batting
    # total looks reasonably balanced.
    # --------------------------------------------------------

    score += (
        normalized_difference(
            stats_a["elite_batters"],
            stats_b["elite_batters"],
        )
        * ELITE_PLAYER_PENALTY
    )

    # --------------------------------------------------------
    # 8. Elite bowling impact
    # --------------------------------------------------------

    score += (
        normalized_difference(
            stats_a["elite_bowlers"],
            stats_b["elite_bowlers"],
        )
        * ELITE_PLAYER_PENALTY
    )

    # --------------------------------------------------------
    # 9. Strong batting impact
    # --------------------------------------------------------

    score += (
        normalized_difference(
            stats_a["strong_batters"],
            stats_b["strong_batters"],
        )
        * STRONG_PLAYER_PENALTY
    )

    # --------------------------------------------------------
    # 10. Strong bowling impact
    # --------------------------------------------------------

    score += (
        normalized_difference(
            stats_a["strong_bowlers"],
            stats_b["strong_bowlers"],
        )
        * STRONG_PLAYER_PENALTY
    )

    # --------------------------------------------------------
    # 11. Weak batting impact
    # --------------------------------------------------------

    score += (
        normalized_difference(
            stats_a["weak_batters"],
            stats_b["weak_batters"],
        )
        * WEAK_PLAYER_PENALTY
    )

    # --------------------------------------------------------
    # 12. Weak bowling impact
    # --------------------------------------------------------

    score += (
        normalized_difference(
            stats_a["weak_bowlers"],
            stats_b["weak_bowlers"],
        )
        * WEAK_PLAYER_PENALTY
    )

    return score


# ============================================================
# RESHUFFLE SCORE
# ============================================================

def reshuffle_score(
    team_a,
    team_b,
    previous_assignment,
):
    """
    Calculate the penalty for moving players between teams.

    Rules:

        A -> A          = 0
        B -> B          = 0

        A -> B          = penalty
        B -> A          = penalty

        SHARED -> A     = 0
        SHARED -> B     = 0

        A -> SHARED     = 0
        B -> SHARED     = 0

        New player      = 0
        Removed player  = 0

    This is important because the objective is not simply to
    create perfectly balanced teams every match.

    We also want to avoid unnecessary player movement.
    """

    # Match 1 has no previous assignment.
    if not previous_assignment:
        return 0

    current_a = {
        p["name"]
        for p in team_a
    }

    current_b = {
        p["name"]
        for p in team_b
    }

    # A shared player appears in both lists.
    current_shared = (
        current_a
        & current_b
    )

    moved_players = 0

    # --------------------------------------------------------
    # Current Team A players
    #
    # Ignore shared players because Shared -> A is not a move.
    # --------------------------------------------------------

    for name in (
        current_a
        - current_shared
    ):

        if (
            previous_assignment.get(name)
            == "B"
        ):

            moved_players += 1

    # --------------------------------------------------------
    # Current Team B players
    #
    # Ignore shared players because Shared -> B is not a move.
    # --------------------------------------------------------

    for name in (
        current_b
        - current_shared
    ):

        if (
            previous_assignment.get(name)
            == "A"
        ):

            moved_players += 1

    return (
        moved_players
        * RESHUFFLE_PENALTY
    )


# ============================================================
# TOTAL SCORE
# ============================================================

def total_score(
    team_a,
    team_b,
    previous_assignment=None,
):
    """
    Combine:

        balance score
        +
        reshuffle penalty

    The optimizer tries to MINIMIZE this number.

    We intentionally do not round the result here.
    """

    balance_score = base_balance_score(
        team_a,
        team_b,
    )

    reshuffle = reshuffle_score(
        team_a,
        team_b,
        previous_assignment,
    )

    return (
        balance_score
        + reshuffle
    )


# ============================================================
# FIND BEST TEAMS
# ============================================================

# ============================================================
# COMPILED EXHAUSTIVE SEARCH HELPERS
# ============================================================

# The optimizer still evaluates every unique valid arrangement.
# Numba compiles the exhaustive-combination loops, and selected-team
# statistics are updated incrementally instead of rebuilding team lists
# and recalculating team_stats() for every candidate.
#
# Metric columns mirror the fields used by base_balance_score().
@njit(cache=False)
def _candidate_score_numba(
    selected_unique_stats,
    total_stats,
    remaining_unique_totals,
    metrics,
    shared_index,
    score_weights,
    movement_count,
    reshuffle_penalty,
):
    """Calculate the same weighted score for one candidate arrangement."""
    balance_score = 0.0
    for metric_index in range(metrics.shape[1]):
        if shared_index >= 0:
            shared_value = metrics[shared_index, metric_index]
            value_a = selected_unique_stats[metric_index] + shared_value
            value_b = (
                remaining_unique_totals[metric_index]
                - selected_unique_stats[metric_index]
                + shared_value
            )
        else:
            value_a = selected_unique_stats[metric_index]
            value_b = total_stats[metric_index] - value_a

        denominator = value_a + value_b
        if denominator != 0.0:
            balance_score += (
                abs(value_a - value_b)
                / denominator
                * score_weights[metric_index]
            )

    return balance_score + movement_count * reshuffle_penalty


@njit(cache=False)
def _next_combination_position(combo, pool_size):
    """Return the rightmost combination position that can be advanced."""
    position = len(combo) - 1
    while position >= 0:
        if combo[position] < pool_size - len(combo) + position:
            return position
        position -= 1
    return -1


@njit(cache=False)
def _recalculate_selected_stats(metrics, fixed_index, pool, combo):
    """Rebase the incremental subset sum periodically to limit float drift."""
    selected = metrics[fixed_index].copy()
    for position in range(len(combo)):
        selected += metrics[pool[combo[position]]]
    return selected


@njit(cache=False)
def _search_even_numba(
    metrics,
    total_stats,
    pool,
    fixed_index,
    choose_count,
    score_weights,
    movement_delta,
    baseline_movement,
    has_previous_assignment,
    reshuffle_penalty,
):
    """Exhaustively search even-player splits with incremental subset sums."""
    pool_size = len(pool)
    combo = np.arange(choose_count, dtype=np.int64)
    selected_stats = metrics[fixed_index].copy()
    selected_movement_delta = 0

    for position in range(choose_count):
        player_index = pool[combo[position]]
        selected_stats += metrics[player_index]
        if has_previous_assignment:
            selected_movement_delta += movement_delta[player_index]

    best_score = float("inf")
    best_choices = np.empty(choose_count, dtype=np.int64)
    candidate_number = 0

    while True:
        movement_count = 0
        if has_previous_assignment:
            movement_count = baseline_movement + selected_movement_delta

        score = _candidate_score_numba(
            selected_stats,
            total_stats,
            total_stats,
            metrics,
            -1,
            score_weights,
            movement_count,
            reshuffle_penalty,
        )

        if score < best_score:
            best_score = score
            for position in range(choose_count):
                best_choices[position] = pool[combo[position]]

        candidate_number += 1
        next_position = _next_combination_position(combo, pool_size)
        if next_position < 0:
            break

        # Remove the old suffix from the running sum/cost.
        for position in range(next_position, choose_count):
            player_index = pool[combo[position]]
            selected_stats -= metrics[player_index]
            if has_previous_assignment:
                selected_movement_delta -= movement_delta[player_index]

        # Advance this combination to the next lexicographic combination.
        combo[next_position] += 1
        for position in range(next_position + 1, choose_count):
            combo[position] = combo[position - 1] + 1

        # Add the new suffix.
        for position in range(next_position, choose_count):
            player_index = pool[combo[position]]
            selected_stats += metrics[player_index]
            if has_previous_assignment:
                selected_movement_delta += movement_delta[player_index]

        # Rebase regularly. This keeps floating-point drift from accumulating
        # while retaining the speed benefit of incremental updates.
        if candidate_number % 64 == 0:
            selected_stats = _recalculate_selected_stats(
                metrics, fixed_index, pool, combo
            )
            selected_movement_delta = 0
            if has_previous_assignment:
                for position in range(choose_count):
                    selected_movement_delta += movement_delta[pool[combo[position]]]

    return best_score, best_choices


@njit(cache=False)
def _search_odd_numba(
    metrics,
    total_stats,
    score_weights,
    movement_delta,
    cost_if_b,
    has_previous_assignment,
    reshuffle_penalty,
):
    """Exhaustively search every possible shared player using incremental sums."""
    player_count = metrics.shape[0]
    unique_team_size = (player_count - 1) // 2
    choose_count = unique_team_size - 1
    metric_count = metrics.shape[1]

    best_score = float("inf")
    best_shared_index = -1
    best_fixed_index = -1
    best_choices = np.empty(choose_count, dtype=np.int64)

    for shared_index in range(player_count):
        remaining = np.empty(player_count - 1, dtype=np.int64)
        cursor = 0
        for player_index in range(player_count):
            if player_index != shared_index:
                remaining[cursor] = player_index
                cursor += 1

        fixed_index = remaining[0]
        pool = remaining[1:]
        pool_size = len(pool)

        # Keep the unique-player totals separate: the shared player is added
        # to both teams and therefore cancels from the skill-difference numerator.
        unique_totals = np.zeros(metric_count, dtype=np.float64)
        remaining_baseline_movement = 0
        for idx in range(len(remaining)):
            player_index = remaining[idx]
            unique_totals += metrics[player_index]
            if has_previous_assignment:
                remaining_baseline_movement += cost_if_b[player_index]

        baseline_movement = remaining_baseline_movement
        if has_previous_assignment:
            baseline_movement += movement_delta[fixed_index]

        combo = np.arange(choose_count, dtype=np.int64)
        selected_stats = metrics[fixed_index].copy()
        selected_movement_delta = 0
        for position in range(choose_count):
            player_index = pool[combo[position]]
            selected_stats += metrics[player_index]
            if has_previous_assignment:
                selected_movement_delta += movement_delta[player_index]

        candidate_number = 0
        while True:
            movement_count = 0
            if has_previous_assignment:
                movement_count = baseline_movement + selected_movement_delta

            score = _candidate_score_numba(
                selected_stats,
                total_stats,
                unique_totals,
                metrics,
                shared_index,
                score_weights,
                movement_count,
                reshuffle_penalty,
            )

            if score < best_score:
                best_score = score
                best_shared_index = shared_index
                best_fixed_index = fixed_index
                for position in range(choose_count):
                    best_choices[position] = pool[combo[position]]

            candidate_number += 1
            next_position = _next_combination_position(combo, pool_size)
            if next_position < 0:
                break

            for position in range(next_position, choose_count):
                player_index = pool[combo[position]]
                selected_stats -= metrics[player_index]
                if has_previous_assignment:
                    selected_movement_delta -= movement_delta[player_index]

            combo[next_position] += 1
            for position in range(next_position + 1, choose_count):
                combo[position] = combo[position - 1] + 1

            for position in range(next_position, choose_count):
                player_index = pool[combo[position]]
                selected_stats += metrics[player_index]
                if has_previous_assignment:
                    selected_movement_delta += movement_delta[player_index]

            if candidate_number % 64 == 0:
                selected_stats = _recalculate_selected_stats(
                    metrics, fixed_index, pool, combo
                )
                selected_movement_delta = 0
                if has_previous_assignment:
                    for position in range(choose_count):
                        selected_movement_delta += movement_delta[pool[combo[position]]]

    return best_score, best_shared_index, best_fixed_index, best_choices


def _player_metric_matrix(players):
    """Precompute the per-player values used by team_stats()."""
    rows = []
    for player in players:
        rows.append([
            player["batting"],
            player["bowling"],
            player["fielding"],
            player_strength(player),
            int(bool(player["is_batsman"])),
            int(bool(player["is_bowler"])),
            int(not player["is_batsman"] and not player["is_bowler"]),
            int(is_elite_batter(player)),
            int(is_elite_bowler(player)),
            int(is_strong_batter(player)),
            int(is_strong_bowler(player)),
            int(is_weak_batter(player)),
            int(is_weak_bowler(player)),
        ])
    return np.asarray(rows, dtype=np.float64)


def _sum_metric_rows(metrics, indices):
    """Sum metric rows in stable player order (matching Python team totals)."""
    result = np.zeros(metrics.shape[1], dtype=np.float64)
    for index in indices:
        result += metrics[index]
    return result


def _score_weight_vector():
    """Weights aligned with metric columns, in the same order as base_balance_score()."""
    return np.asarray([
        SKILL_WEIGHTS["batting"],
        SKILL_WEIGHTS["bowling"],
        SKILL_WEIGHTS["fielding"],
        OVERALL_STRENGTH_PENALTY,
        ROLE_PENALTIES["batsmen"],
        ROLE_PENALTIES["bowlers"],
        ROLE_PENALTIES["fielders"],
        ELITE_PLAYER_PENALTY,
        ELITE_PLAYER_PENALTY,
        STRONG_PLAYER_PENALTY,
        STRONG_PLAYER_PENALTY,
        WEAK_PLAYER_PENALTY,
        WEAK_PLAYER_PENALTY,
    ], dtype=np.float64)


def _reshuffle_cost_arrays(players, previous_assignment):
    """Return per-player movement costs for assignment to Team A and Team B."""
    if not previous_assignment:
        zeros = np.zeros(len(players), dtype=np.int64)
        return zeros, zeros.copy()

    cost_if_a = np.asarray([
        int(previous_assignment.get(player["name"]) == "B")
        for player in players
    ], dtype=np.int64)
    cost_if_b = np.asarray([
        int(previous_assignment.get(player["name"]) == "A")
        for player in players
    ], dtype=np.int64)
    return cost_if_a, cost_if_b


def find_best_teams(
    players,
    previous_assignment=None,
):
    """Find the global best split using compiled exhaustive search.

    The scoring formula and candidate search space are unchanged. This
    implementation precomputes per-player metrics and updates selected-team
    sums incrementally as combinations advance, avoiding repeated Python
    list construction and repeated calls to team_stats() for every candidate.
    """
    if len(players) < 2:
        raise ValueError("At least 2 players are required.")

    players = list(players)
    metrics = _player_metric_matrix(players)
    total_stats = _sum_metric_rows(metrics, range(len(players)))
    score_weights = _score_weight_vector()
    cost_if_a, cost_if_b = _reshuffle_cost_arrays(players, previous_assignment)
    movement_delta = cost_if_a - cost_if_b
    has_previous_assignment = bool(previous_assignment)

    if len(players) % 2 == 0:
        fixed_index = 0
        pool = np.arange(1, len(players), dtype=np.int64)
        baseline_movement = 0
        if has_previous_assignment:
            baseline_movement = int(
                cost_if_b.sum() + movement_delta[fixed_index]
            )

        best_score, best_choices = _search_even_numba(
            metrics,
            total_stats,
            pool,
            fixed_index,
            len(players) // 2 - 1,
            score_weights,
            movement_delta,
            baseline_movement,
            has_previous_assignment,
            RESHUFFLE_PENALTY,
        )
        best_shared_index = -1
        best_fixed_index = fixed_index
        best_choice_indices = best_choices.tolist()
    else:
        best_score, best_shared_index, best_fixed_index, best_choices = _search_odd_numba(
            metrics,
            total_stats,
            score_weights,
            movement_delta,
            cost_if_b,
            has_previous_assignment,
            RESHUFFLE_PENALTY,
        )
        best_choice_indices = best_choices.tolist()

    if best_fixed_index < 0:
        raise RuntimeError("Unable to generate teams.")

    # Rebuild teams in the same order as the prior implementation.
    team_a_unique_indices = [best_fixed_index] + best_choice_indices
    team_a_unique_set = set(team_a_unique_indices)

    if best_shared_index < 0:
        team_a = [players[i] for i in team_a_unique_indices]
        team_b = [
            player for i, player in enumerate(players)
            if i not in team_a_unique_set
        ]
        shared_player = None
    else:
        remaining_indices = [
            i for i in range(len(players))
            if i != best_shared_index
        ]
        team_b_unique = [
            players[i] for i in remaining_indices
            if i not in team_a_unique_set
        ]
        shared_player = players[best_shared_index]
        team_a = [players[i] for i in team_a_unique_indices] + [shared_player]
        team_b = team_b_unique + [shared_player]

    # Use the original scalar helpers to report the scores. This keeps the
    # returned score fields consistent with the rest of the application.
    balance_score = base_balance_score(team_a, team_b)
    reshuffle = reshuffle_score(team_a, team_b, previous_assignment)
    return {
        "team_a": team_a,
        "team_b": team_b,
        "shared_player": shared_player,
        "score": balance_score + reshuffle,
        "balance_score": balance_score,
        "reshuffle_score": reshuffle,
    }
