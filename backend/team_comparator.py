"""
Team comparison calculations.

This module calculates statistics for manually created teams.

It does NOT decide which team is better.

The purpose is to give the user objective numbers so that they
can compare teams themselves.

The existing team_balancer.py remains responsible for the
automatic 2-team balancing algorithm.
"""

from backend.team_balancer import (
    player_strength,
    team_stats,
)


def calculate_team_comparison(team):
    """
    Calculate statistics for one manually created team.

    We reuse team_stats() from the existing balancing engine
    so that batting, bowling, fielding and overall-strength
    calculations remain consistent throughout the application.

    Returns both totals and averages.
    """

    stats = team_stats(team)

    player_count = len(team)

    # --------------------------------------------------------
    # Empty team
    # --------------------------------------------------------
    #
    # An empty team is valid while the user is building teams.
    # Return zero values instead of attempting to divide by zero.
    # --------------------------------------------------------

    if player_count == 0:

        return {
            "player_count": 0,

            "batting_total": 0.0,
            "batting_average": 0.0,

            "bowling_total": 0.0,
            "bowling_average": 0.0,

            "fielding_total": 0.0,
            "fielding_average": 0.0,

            "strength_total": 0.0,
            "strength_average": 0.0,

            "batsmen": 0,
            "bowlers": 0,

            "elite_batters": 0,
            "elite_bowlers": 0,

            "strong_batters": 0,
            "strong_bowlers": 0,
        }

    # --------------------------------------------------------
    # Team statistics
    # --------------------------------------------------------
    #
    # IMPORTANT:
    #
    # These key names must match the dictionary returned by
    # your existing team_stats() function.
    #
    # Your existing balancer uses:
    #
    #     elite_batters
    #     strong_batters
    #
    # rather than:
    #
    #     elite_batsmen
    #     strong_batsmen
    # --------------------------------------------------------

    return {
        "player_count": player_count,

        # ----------------------------------------------------
        # Skill totals
        # ----------------------------------------------------

        "batting_total": stats["batting"],
        "bowling_total": stats["bowling"],
        "fielding_total": stats["fielding"],

        # ----------------------------------------------------
        # Skill averages
        # ----------------------------------------------------

        "batting_average": (
            stats["batting"] / player_count
        ),

        "bowling_average": (
            stats["bowling"] / player_count
        ),

        "fielding_average": (
            stats["fielding"] / player_count
        ),

        # ----------------------------------------------------
        # Overall strength
        # ----------------------------------------------------

        "strength_total": stats["strength"],

        "strength_average": (
            stats["strength"] / player_count
        ),

        # ----------------------------------------------------
        # Role counts
        # ----------------------------------------------------

        "batsmen": stats["batsmen"],
        "bowlers": stats["bowlers"],

        # ----------------------------------------------------
        # Impact-tier counts
        # ----------------------------------------------------

        "elite_batters": stats["elite_batters"],
        "elite_bowlers": stats["elite_bowlers"],

        "strong_batters": stats["strong_batters"],
        "strong_bowlers": stats["strong_bowlers"],
    }


def compare_teams(teams):
    """
    Calculate comparison statistics for all teams.

    Input:

        {
            "Team A": [player, player, ...],
            "Team B": [player, player, ...],
            "Team C": [player, player, ...]
        }

    Output:

        {
            "Team A": {...statistics...},
            "Team B": {...statistics...},
            "Team C": {...statistics...}
        }
    """

    return {
        team_name: calculate_team_comparison(
            players
        )
        for team_name, players in teams.items()
    }


def order_players_by_strength(players):
    """
    Sort players from highest to lowest overall strength.

    This is ONLY for presentation.

    It does not affect:
        - team assignments
        - team comparison
        - the existing balancing algorithm
    """

    return sorted(
        players,
        key=player_strength,
        reverse=True,
    )