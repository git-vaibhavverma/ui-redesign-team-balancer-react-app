# ============================================================
# TEAM BALANCER CONFIGURATION
# ============================================================
#
# This file contains the "knobs" used by the balancing engine.
#
# The algorithm itself lives in:
#     backend/team_balancer.py
#
# If we later want to tune how teams are balanced, this is the
# first place we should look.
# ============================================================


# ------------------------------------------------------------
# SKILL WEIGHTS
# ------------------------------------------------------------
#
# These determine how much each skill contributes to the
# overall skill-balance calculation.
#
# Current thinking:
#   Bowling is slightly more important than batting because
#   we want both teams to have sufficient bowling resources.
#
# The weights don't have to add up to 1.0 mathematically,
# but keeping them normalized makes them easier to understand.
# ------------------------------------------------------------

SKILL_WEIGHTS = {
    "batting": 0.40,
    "bowling": 0.40,
    "fielding": 0.20,
}


# ------------------------------------------------------------
# ROLE PENALTIES
# ------------------------------------------------------------
#
# Two teams could have similar skill totals but very different
# compositions.
#
# Example:
#   Team A -> 5 batsmen, 2 bowlers
#   Team B -> 2 batsmen, 5 bowlers
#
# These penalties make the algorithm care about that difference.
# ------------------------------------------------------------


ROLE_PENALTIES = {
    "batsmen": 0.10,
    "bowlers": 0.10,
    "fielders": 0.10,
}

# ------------------------------------------------------------
# OVERALL STRENGTH PENALTY
# ------------------------------------------------------------
#
# player_strength() creates a weighted overall strength for
# every player.
#
# This penalty makes the algorithm consider the total weighted
# strength of both teams in addition to individual skill totals.
# ------------------------------------------------------------

OVERALL_STRENGTH_PENALTY = 1.00


# ------------------------------------------------------------
# IMPACT THRESHOLDS
# ------------------------------------------------------------
#
# These are deliberately separate from the skill weights.
#
# Elite:
#     rating >= 9.00
#
# Strong:
#     7.00 <= rating < 9.00
#
# Normal:
#     rating < 7.00
#
# IMPORTANT:
# Strong and Elite are mutually exclusive.
# A player with 9.35 is Elite, NOT Strong.
# ------------------------------------------------------------

IMPACT_THRESHOLDS = {
    "elite": 8.50,
    "strong": 7.00,
    "weak": 5.00,
}


# ------------------------------------------------------------
# IMPACT PENALTIES
# ------------------------------------------------------------
#
# If one team has significantly more Elite/Strong players than
# the other, the balance score should reflect that.
#
# Elite players receive a larger penalty because they represent
# a greater concentration of high-impact ability.
# ------------------------------------------------------------

ELITE_PLAYER_PENALTY = 0.20

STRONG_PLAYER_PENALTY = 0.10

WEAK_PLAYER_PENALTY = 0.10


# ------------------------------------------------------------
# RESHUFFLE PENALTY
# ------------------------------------------------------------
#
# We don't want the algorithm to completely reshuffle teams
# every time the player list changes.
#
# An actual A -> B or B -> A movement receives this penalty.
#
# Important:
#   Shared -> A
#   Shared -> B
#   A -> Shared
#   B -> Shared
#
# are NOT considered moves.
# ------------------------------------------------------------

RESHUFFLE_PENALTY = 0.01