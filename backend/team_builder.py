"""
Manual multi-team builder.

This module is separate from the existing team_balancer.py.

The existing team_balancer.py is responsible for automatically
finding the best 2-team split.

This module does something different:

    The user manually selects players and assigns them to
    Team A, Team B, Team C, etc.

No optimization happens here.

Players that have not been assigned to any team remain in the
available player pool.
"""


class TeamBuilder:

    def __init__(self, players):
        """
        Initialize the Team Builder with the master player pool.

        We store players by name so that:
            - checking whether a player exists is easy
            - checking whether a player is already assigned is easy
            - retrieving the complete player object is easy

        The original master player list is not modified.
        """

        self.players = {
            player["name"]: player
            for player in players
        }

        # Stores the manual team assignments.
        #
        # Example:
        #
        # {
        #     "Team A": ["Aseem", "Joyash", "KD"],
        #     "Team B": ["Rutik", "Manya"]
        # }
        #
        # Only player names are stored here. The actual player
        # details continue to come from self.players.
        self.teams = {}

    def add_team(self, team_name):
        """
        Create a new empty team.

        Team names must be non-empty and unique.
        """

        team_name = team_name.strip()

        if not team_name:
            raise ValueError(
                "Team name cannot be empty."
            )

        if team_name in self.teams:
            raise ValueError(
                f"Team '{team_name}' already exists."
            )

        self.teams[team_name] = []

    def remove_team(self, team_name):
        """
        Remove an existing team.

        Removing the team automatically makes all of its
        players available again.

        This is useful when the user wants to completely
        rebuild a team.
        """

        if team_name not in self.teams:
            raise ValueError(
                f"Team '{team_name}' does not exist."
            )

        del self.teams[team_name]

    def get_assigned_player_names(self):
        """
        Return the names of every player currently assigned
        to any team.

        This is used to determine which players should be
        removed from the available pool.
        """

        assigned_players = set()

        for player_names in self.teams.values():
            assigned_players.update(player_names)

        return assigned_players

    def get_available_players(self):
        """
        Return all players who are not currently assigned
        to any manually created team.

        IMPORTANT:

        There is intentionally NO requirement that every player
        must be assigned.

        For example, with 34 players:

            Team A = 7
            Team B = 7

        leaves 20 players available.
        """

        assigned_players = (
            self.get_assigned_player_names()
        )

        return [
            player
            for name, player in self.players.items()
            if name not in assigned_players
        ]

    def add_player_to_team(
        self,
        player_name,
        team_name,
    ):
        """
        Assign a player to a team.

        A player can belong to only ONE manually created team.

        This prevents the same player from accidentally being
        selected for Team A and Team B simultaneously.
        """

        if player_name not in self.players:
            raise ValueError(
                f"Player '{player_name}' does not exist."
            )

        if team_name not in self.teams:
            raise ValueError(
                f"Team '{team_name}' does not exist."
            )

        if player_name in self.get_assigned_player_names():
            raise ValueError(
                f"Player '{player_name}' is already "
                "assigned to a team."
            )

        self.teams[team_name].append(
            player_name
        )

    def remove_player_from_team(
        self,
        player_name,
        team_name,
    ):
        """
        Remove a player from a team.

        The player immediately becomes available in the
        available-player pool again.
        """

        if team_name not in self.teams:
            raise ValueError(
                f"Team '{team_name}' does not exist."
            )

        if player_name not in self.teams[team_name]:
            raise ValueError(
                f"Player '{player_name}' is not in "
                f"'{team_name}'."
            )

        self.teams[team_name].remove(
            player_name
        )

    def get_team_players(self, team_name):
        """
        Return the complete player dictionaries for a team.

        The team internally stores only player names, but the UI
        needs the full player information such as batting,
        bowling and fielding ratings.
        """

        if team_name not in self.teams:
            raise ValueError(
                f"Team '{team_name}' does not exist."
            )

        return [
            self.players[player_name]
            for player_name in self.teams[team_name]
        ]

    def get_all_teams(self):
        """
        Return all teams with their complete player objects.

        Example:

        {
            "Team A": [
                {...player details...},
                {...player details...}
            ],
            "Team B": [
                {...player details...}
            ]
        }
        """

        return {
            team_name: self.get_team_players(
                team_name
            )
            for team_name in self.teams
        }

    def clear(self):
        """
        Remove all teams.

        This effectively resets the Team Builder and returns
        every player to the available pool.
        """

        self.teams.clear()