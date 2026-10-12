# ============================================================
# PLAYER SERVICE
# ============================================================
#
# Responsibilities:
#
#   1. Load the master player CSV.
#   2. Convert CSV values into the format expected by the
#      backend.
#   3. Validate player information.
#   4. Normalize ratings to two decimal places.
#
# The team-balancing engine should NOT know that players came
# from a CSV file. This separation will be useful when we later
# replace Streamlit/CSV with an API/database/frontend.
# ============================================================

from numbers import Real

import pandas as pd


class PlayerService:

    def __init__(self, csv_path):
        """
        Store the location of the master player CSV.
        """

        self.csv_path = csv_path

    def load_master_players(self):
        """
        Load the complete master player pool.

        IMPORTANT:
        The master list is NOT the list of players playing
        the current match.

        Example:

            Master pool = 16 players
            Match 1      = 12 players

        The frontend decides which 12 players participate.
        """

        df = pd.read_csv(
            self.csv_path
        )

        # ----------------------------------------------------
        # Convert TRUE/FALSE CSV values into Python booleans.
        #
        # This handles values such as:
        #   TRUE
        #   true
        #   True
        # ----------------------------------------------------

        boolean_columns = [
            "is_batsman",
            "is_bowler",
        ]

        for column in boolean_columns:

            df[column] = (
                df[column]
                .astype(str)
                .str.upper()
                .eq("TRUE")
            )

        # ----------------------------------------------------
        # Convert ratings into floating-point numbers.
        #
        # Example:
        #
        #   9     -> 9.00
        #   9.35  -> 9.35
        #
        # We normalize to two decimal places at the input
        # boundary because your teammate averages are
        # intentionally stored to two decimal places.
        # ----------------------------------------------------

        rating_columns = [
            "batting",
            "bowling",
            "fielding",
        ]

        for column in rating_columns:

            df[column] = (
                pd.to_numeric(
                    df[column],
                    errors="raise",
                )
                .astype(float)
                .round(2)
            )

        # Convert the DataFrame into ordinary Python dictionaries.
        #
        # From this point onward, the core backend does not need
        # pandas.
        players = df.to_dict(
            "records"
        )

        # Validate every player before making the data available
        # to the rest of the application.
        for player in players:

            self.validate_player(
                player
            )

        return players

    @staticmethod
    def validate_player(player):
        """
        Validate one player record.

        This method is also used when players are added to a
        running session, so invalid data cannot accidentally
        enter the balancing engine.
        """

        # ----------------------------------------------------
        # Required fields
        # ----------------------------------------------------

        required_fields = [
            "name",
            "batting",
            "bowling",
            "fielding",
            "is_batsman",
            "is_bowler",
        ]

        for field in required_fields:

            if field not in player:

                raise ValueError(
                    f"Missing player field: {field}"
                )

        # ----------------------------------------------------
        # Player name validation
        # ----------------------------------------------------

        if not str(
            player["name"]
        ).strip():

            raise ValueError(
                "Player name cannot be empty."
            )

        # ----------------------------------------------------
        # Rating validation
        #
        # Ratings may be:
        #
        #   1
        #   7
        #   8.25
        #   9.73
        #
        # but must remain within 1-10.
        # ----------------------------------------------------

        rating_columns = [
            "batting",
            "bowling",
            "fielding",
        ]

        for skill in rating_columns:

            value = player[skill]

            if not isinstance(
                value,
                Real,
            ):

                raise ValueError(
                    f"{skill} must be a number."
                )

            if not 1 <= value <= 10:

                raise ValueError(
                    f"{skill} must be between 1 and 10."
                )

            # Normalize the value once at the boundary.
            #
            # We do NOT repeatedly round this value inside the
            # balancing calculations.
            player[skill] = round(
                float(value),
                2,
            )