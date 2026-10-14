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
import math

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
    # SESSION SNAPSHOT / RESTORE
    # ========================================================

    @staticmethod
    def _match_to_snapshot(result):
        """Serialize a generated match using player names and score metrics only."""
        if result is None:
            return None

        shared_player = result.get("shared_player")
        if isinstance(shared_player, dict):
            shared_player = shared_player.get("name")

        return {
            "team_a": [str(player["name"]) for player in result.get("team_a", [])],
            "team_b": [str(player["name"]) for player in result.get("team_b", [])],
            "shared_player": shared_player,
            "score": float(result.get("score", 0.0)),
            "balance_score": float(result.get("balance_score", 0.0)),
            "reshuffle_score": float(result.get("reshuffle_score", 0.0)),
        }

    def to_snapshot(self):
        """Return JSON-friendly session state that can survive an API restart.

        Player records are represented by names because the trusted master roster
        remains on the server. Restore rebuilds player dictionaries from that roster.
        """
        return {
            "version": 1,
            "match_number": int(self.match_number),
            "player_names": [str(player["name"]) for player in self.players],
            "current_match": self._match_to_snapshot(self.current_teams),
            "history": [self._match_to_snapshot(match) for match in self.history],
        }

    @classmethod
    def from_snapshot(cls, snapshot, master_players):
        """Rebuild a CricketSession from a validated, JSON-friendly snapshot.

        The master roster is authoritative: browser-supplied ratings/roles are never
        trusted, and all restored players are reconstructed from master player data.
        """
        if not isinstance(snapshot, dict) or snapshot.get("version") != 1:
            raise ValueError("Unsupported or invalid session snapshot.")

        master_by_name = {
            str(player.get("name", "")): player
            for player in master_players
            if isinstance(player, dict) and player.get("name")
        }

        def validate_names(raw_names, field_name):
            if not isinstance(raw_names, list) or len(raw_names) > 200:
                raise ValueError("Invalid player list in session snapshot: " + field_name)
            names = []
            for raw_name in raw_names:
                if not isinstance(raw_name, str) or not raw_name.strip():
                    raise ValueError("Invalid player name in session snapshot: " + field_name)
                name = raw_name.strip()
                if name not in master_by_name:
                    raise ValueError("Unknown player in session snapshot: " + name)
                names.append(name)
            if len(set(names)) != len(names):
                raise ValueError("Duplicate player names in session snapshot: " + field_name)
            return names

        def canonical_player(name):
            return deepcopy(master_by_name[name])

        def finite_score(match, key):
            value = match.get(key, 0.0)
            if isinstance(value, bool):
                raise ValueError("Invalid match score in session snapshot.")
            try:
                number = float(value)
            except (TypeError, ValueError):
                raise ValueError("Invalid match score in session snapshot.")
            if not math.isfinite(number):
                raise ValueError("Invalid match score in session snapshot.")
            return number

        def restore_match(raw_match, field_name):
            if raw_match is None:
                return None
            if not isinstance(raw_match, dict):
                raise ValueError("Invalid match entry in session snapshot: " + field_name)

            team_a_names = validate_names(raw_match.get("team_a"), field_name + ".team_a")
            team_b_names = validate_names(raw_match.get("team_b"), field_name + ".team_b")
            shared_name = raw_match.get("shared_player")
            if shared_name is not None:
                if not isinstance(shared_name, str) or shared_name not in master_by_name:
                    raise ValueError("Invalid shared player in session snapshot.")

            overlap = set(team_a_names) & set(team_b_names)
            expected_overlap = {shared_name} if shared_name is not None else set()
            if overlap != expected_overlap:
                raise ValueError("Team membership is inconsistent in session snapshot.")

            return {
                "team_a": [canonical_player(name) for name in team_a_names],
                "team_b": [canonical_player(name) for name in team_b_names],
                "shared_player": canonical_player(shared_name) if shared_name else None,
                "score": finite_score(raw_match, "score"),
                "balance_score": finite_score(raw_match, "balance_score"),
                "reshuffle_score": finite_score(raw_match, "reshuffle_score"),
            }

        raw_match_number = snapshot.get("match_number")
        if isinstance(raw_match_number, bool):
            raise ValueError("Invalid match number in session snapshot.")
        try:
            match_number = int(raw_match_number)
        except (TypeError, ValueError):
            raise ValueError("Invalid match number in session snapshot.")
        if match_number < 0 or match_number > 5000:
            raise ValueError("Invalid match number in session snapshot.")

        player_names = validate_names(snapshot.get("player_names"), "player_names")
        raw_history = snapshot.get("history")
        if not isinstance(raw_history, list) or len(raw_history) > 5000:
            raise ValueError("Invalid match history in session snapshot.")
        if len(raw_history) != match_number:
            raise ValueError("Match history does not match the saved match number.")

        history = [
            restore_match(raw_match, "history[{}]".format(index))
            for index, raw_match in enumerate(raw_history)
        ]
        current_match = restore_match(snapshot.get("current_match"), "current_match")

        if match_number == 0 and current_match is not None:
            raise ValueError("A session with no generated matches cannot have a current match.")
        if match_number > 0 and (current_match is None or not history):
            raise ValueError("The current match is missing from the saved session.")
        if current_match is not None:
            current_names = {
                player["name"] for player in current_match["team_a"] + current_match["team_b"]
            }
            if not current_names.issubset(set(player_names)):
                raise ValueError("Current team contains players outside the saved roster.")

        session = cls()
        session.players = [canonical_player(name) for name in player_names]
        session.match_number = match_number
        session.current_teams = current_match
        session.history = history
        return session

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