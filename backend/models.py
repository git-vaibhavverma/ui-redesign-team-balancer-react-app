# ============================================================
# DATA MODELS
# ============================================================
#
# This file contains simple Python data models used by the
# backend.
#
# Keeping these models separate from the balancing algorithm
# makes the backend easier to reuse later through an API.
# ============================================================

from dataclasses import dataclass


@dataclass
class Player:
    """
    Represents a cricket player.

    Ratings are floats because player ratings can contain
    decimal values, for example:

        batting  = 9.35
        bowling  = 8.82
        fielding = 9.47

    The application keeps these ratings to two decimal places
    at the input boundary.
    """

    name: str

    batting: float
    bowling: float
    fielding: float

    is_batsman: bool
    is_bowler: bool

    def to_dict(self):
        """
        Convert the Player object into a normal dictionary.

        This is useful when communicating with Streamlit,
        JSON APIs, or other parts of the application that
        expect dictionaries.
        """

        return {
            "name": self.name,
            "batting": self.batting,
            "bowling": self.bowling,
            "fielding": self.fielding,
            "is_batsman": self.is_batsman,
            "is_bowler": self.is_bowler,
        }


@dataclass
class MatchResult:
    """
    Represents the result produced by the team-balancing engine.

    team_a and team_b contain player dictionaries.

    When the number of players is odd, shared_player contains
    the player who appears in both teams.
    """

    team_a: list
    team_b: list

    shared_player: dict | None

    # The optimizer's total score.
    score: float

    # Score representing only team balance.
    balance_score: float

    # Score representing only reshuffling.
    reshuffle_score: float

    def to_dict(self):
        """
        Convert the MatchResult into a dictionary.

        Useful for Streamlit today and potentially an API later.
        """

        return {
            "team_a": self.team_a,
            "team_b": self.team_b,
            "shared_player": self.shared_player,
            "score": self.score,
            "balance_score": self.balance_score,
            "reshuffle_score": self.reshuffle_score,
        }


@dataclass
class ManualTeam:
    """
    Represents a manually created team in the Team Builder.

    This is intentionally separate from MatchResult because
    these teams are user-created rather than algorithmically
    generated for a Sunday match.
    """

    name: str
    players: list

    def to_dict(self):
        return {
            "name": self.name,
            "players": self.players,
        }