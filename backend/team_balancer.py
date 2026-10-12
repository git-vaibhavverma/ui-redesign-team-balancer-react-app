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
# (typically around 10-20 players).
# ============================================================

from itertools import combinations

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

def find_best_teams(
    players,
    previous_assignment=None,
):
    """
    Find the best possible team arrangement.

    EVEN number of players:
        Players are split equally.

    ODD number of players:
        Exactly one player is shared between the two teams.

    The algorithm evaluates every possible valid arrangement.

    Because our Sunday group is relatively small, exhaustive
    search is practical and gives us confidence that we're not
    relying on a heuristic that might miss a better combination.
    """

    if len(players) < 2:

        raise ValueError(
            "At least 2 players are required."
        )

    # Make a copy so we don't accidentally modify the caller's
    # player list.
    players = list(players)

    best_result = None

    # We are minimizing the score, so start with infinity.
    best_score = float("inf")

    player_count = len(players)

    # ========================================================
    # EVEN NUMBER OF PLAYERS
    # ========================================================

    if player_count % 2 == 0:

        team_size = (
            player_count // 2
        )

        # ----------------------------------------------------
        # Symmetry optimization
        #
        # Team A / Team B and Team B / Team A represent the
        # same split.
        #
        # We therefore force the first player into Team A.
        # This roughly halves the number of combinations we
        # need to evaluate.
        # ----------------------------------------------------

        first_player = players[0]

        remaining_players = players[1:]

        # Choose the remaining players needed to complete
        # Team A.
        for team_a_rest in combinations(
            remaining_players,
            team_size - 1,
        ):

            team_a = [
                first_player,
                *team_a_rest,
            ]

            team_a_names = {
                p["name"]
                for p in team_a
            }

            # Everyone not in Team A becomes Team B.
            team_b = [
                p
                for p in players
                if p["name"]
                not in team_a_names
            ]

            score = total_score(
                team_a,
                team_b,
                previous_assignment,
            )

            # Keep the best arrangement found so far.
            if score < best_score:

                best_score = score

                best_result = {
                    "team_a": team_a,
                    "team_b": team_b,

                    # Even player count means nobody is shared.
                    "shared_player": None,

                    "score": score,

                    "balance_score":
                        base_balance_score(
                            team_a,
                            team_b,
                        ),

                    "reshuffle_score":
                        reshuffle_score(
                            team_a,
                            team_b,
                            previous_assignment,
                        ),
                }

    # ========================================================
    # ODD NUMBER OF PLAYERS
    # ========================================================

    else:

        # ----------------------------------------------------
        # With an odd number of players, exactly one player is
        # shared between both teams.
        #
        # Example:
        #
        # 13 players
        #
        # One shared player
        # 12 unique player slots
        #
        # 6 unique players + shared
        #        VS
        # 6 unique players + shared
        # ----------------------------------------------------

        unique_count = (
            player_count - 1
        )

        unique_team_size = (
            unique_count // 2
        )

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # We try EVERY player as the shared player.
        #
        # This allows the algorithm to decide which player
        # produces the best overall balance.
        # ----------------------------------------------------

        for shared_player in players:

            remaining_players = [
                p
                for p in players
                if p["name"]
                != shared_player["name"]
            ]

            # Again use the first remaining player to eliminate
            # mirror-image Team A / Team B combinations.
            first_player = (
                remaining_players[0]
            )

            remaining_after_first = (
                remaining_players[1:]
            )

            # Select the remaining players required for
            # Team A's unique portion.
            for team_a_rest in combinations(
                remaining_after_first,
                unique_team_size - 1,
            ):

                team_a_unique = [
                    first_player,
                    *team_a_rest,
                ]

                team_a_names = {
                    p["name"]
                    for p in team_a_unique
                }

                # Everyone else becomes Team B's unique players.
                team_b_unique = [
                    p
                    for p in remaining_players
                    if p["name"]
                    not in team_a_names
                ]

                # Add the same shared player to both teams.
                team_a = [
                    *team_a_unique,
                    shared_player,
                ]

                team_b = [
                    *team_b_unique,
                    shared_player,
                ]

                score = total_score(
                    team_a,
                    team_b,
                    previous_assignment,
                )

                if score < best_score:

                    best_score = score

                    best_result = {
                        "team_a": team_a,
                        "team_b": team_b,

                        "shared_player":
                            shared_player,

                        "score": score,

                        "balance_score":
                            base_balance_score(
                                team_a,
                                team_b,
                            ),

                        "reshuffle_score":
                            reshuffle_score(
                                team_a,
                                team_b,
                                previous_assignment,
                            ),
                    }

    # This should never happen if the input is valid, but it's
    # safer to fail explicitly than return None.
    if best_result is None:

        raise RuntimeError(
            "Unable to generate teams."
        )

    return best_result