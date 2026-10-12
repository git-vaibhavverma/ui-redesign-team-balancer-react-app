# ============================================================
# CRICKET SESSION MANAGER
# ============================================================
#
# This class manages one Sunday cricket session.
#
# Responsibilities:
#
#   - Keep track of participating players.
#   - Add/remove players between matches.
#   - Remember the current team assignment.
#   - Keep match history.
#   - Ask the balancing engine to generate the next match.
#
# The important separation is:
#
#   Streamlit UI
#        ↓
#   CricketSession
#        ↓
#   Team Balancer
#
# This means the UI does not need to understand how teams
# are actually calculated.
# ============================================================

from copy import deepcopy

from backend.player_service import PlayerService
from backend.team_balancer import find_best_teams


class CricketSession:

    def __init__(self):
        """
        Create an empty cricket session.

        No players are participating initially because Match 1
        selection is handled by the frontend.
        """

        # Players currently participating in the session.
        self.players = []

        # Result of the most recently generated match.
        self.current_teams = None

        # Number of matches already generated.
        self.match_number = 0

        # Complete history of generated matches.
        self.history = []

    # ========================================================
    # INITIAL PLAYER SETUP
    # ========================================================

    def set_initial_players(self, players):
        """
        Set the players participating in Match 1.

        This can only be done before the first match.

        The method also validates every player before adding
        them to the session.
        """

        if self.match_number > 0:

            raise ValueError(
                "Initial players can only be set before Match 1."
            )

        validated_players = []

        for player in players:

            # Work on a copy so validation/normalization does
            # not unexpectedly modify the original master data.
            player_copy = player.copy()

            PlayerService.validate_player(
                player_copy
            )

            validated_players.append(
                player_copy
            )

        self.players = (
            validated_players
        )

    # ========================================================
    # ADD PLAYER
    # ========================================================

    def add_player(self, player):
        """
        Add an existing master player to the current session.

        This is normally used when someone joins between matches.

        The newly added player has no previous team assignment,
        so the balancing engine is free to place them anywhere.
        """

        player_copy = player.copy()

        # Validate before allowing the player into the session.
        PlayerService.validate_player(
            player_copy
        )

        existing_names = {
            p["name"]
            for p in self.players
        }

        if (
            player_copy["name"]
            in existing_names
        ):

            raise ValueError(
                f"Player '{player_copy['name']}' "
                "is already participating."
            )

        self.players.append(
            player_copy
        )

    # ========================================================
    # REMOVE PLAYER
    # ========================================================

    def remove_player(self, player_name):
        """
        Remove a player from the current session.

        The balancing engine naturally treats a removed player
        as no longer available.

        A removed player therefore receives no reshuffle penalty.
        """

        original_count = len(
            self.players
        )

        self.players = [
            p
            for p in self.players
            if p["name"] != player_name
        ]

        # If the count didn't change, the requested player
        # didn't exist.
        if len(self.players) == original_count:

            raise ValueError(
                f"Player '{player_name}' "
                "was not found."
            )

    # ========================================================
    # GET PREVIOUS ASSIGNMENT
    # ========================================================

    def get_previous_assignment(self):
        """
        Convert the previous match result into a simple mapping.

        Example:

            {
                "Aseem": "A",
                "Joyash": "A",
                "Rutik": "B",
                "Manya": "B",
                "Vaibhav": "SHARED"
            }

        This mapping is what the balancing engine uses to
        calculate reshuffling.

        Important:
        A shared player appears in BOTH team lists, so the
        intersection of Team A and Team B identifies the
        shared player.
        """

        if not self.current_teams:
            return None

        team_a_names = {
            p["name"]
            for p in self.current_teams["team_a"]
        }

        team_b_names = {
            p["name"]
            for p in self.current_teams["team_b"]
        }

        assignment = {}

        # ----------------------------------------------------
        # Shared players
        # ----------------------------------------------------

        for name in (
            team_a_names
            & team_b_names
        ):

            assignment[name] = "SHARED"

        # ----------------------------------------------------
        # Team A only
        # ----------------------------------------------------

        for name in (
            team_a_names
            - team_b_names
        ):

            assignment[name] = "A"

        # ----------------------------------------------------
        # Team B only
        # ----------------------------------------------------

        for name in (
            team_b_names
            - team_a_names
        ):

            assignment[name] = "B"

        return assignment

    # ========================================================
    # GENERATE MATCH
    # ========================================================

    def generate_match(self):
        """
        Generate the next balanced match.

        Steps:

            1. Validate minimum player count.
            2. Get the previous assignment.
            3. Ask the team-balancing engine for the best teams.
            4. Increment the match number.
            5. Save the current result.
            6. Add a copy to history.
            7. Return the result.
        """

        if len(self.players) < 2:

            raise ValueError(
                "At least 2 players are required."
            )

        # The previous assignment is used to minimize
        # unnecessary A <-> B movements.
        previous_assignment = (
            self.get_previous_assignment()
        )

        # The session manager does not decide which teams are
        # best. That responsibility belongs to the balancing
        # engine.
        result = find_best_teams(
            self.players,
            previous_assignment,
        )

        self.match_number += 1

        self.current_teams = result

        # deepcopy is important here.
        #
        # We want the history entry to represent what happened
        # at this moment, even if future code changes objects.
        self.history.append(
            deepcopy(result)
        )

        return result