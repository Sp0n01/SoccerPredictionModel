from dataclasses import dataclass
import pandas as pd

@dataclass
class EloConfig:
    initial_rating: float = 1500.0
    k_factor: float = 20.0
    home_advantage: float = 60.0
    margin_of_victory: bool = True

class EloRatingSystem:
    def __init__(self, config: EloConfig = None):
        self.config = config or EloConfig()
        self.ratings: dict[str, float] = {}

    def get_rating(self, team: str) -> float:
        return self.ratings.get(team, self.config.initial_rating)

    def expected_score(self, rating_a: float, rating_b: float) -> float:
        return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))

    def margin_multiplier(self, goal_diff: int) -> float:
        if not self.config.margin_of_victory:
            return 1.0
        return (abs(goal_diff) + 1) ** 0.5 if goal_diff != 0 else 1.0

    def process_match(self, home_team: str, away_team: str,
                      home_goals: int, away_goals: int) -> tuple[float, float]:

        home_rating = self.get_rating(home_team)
        away_rating = self.get_rating(away_team)

        # Expected score uses home-adjusted rating.
        expected_home = self.expected_score(
            home_rating + self.config.home_advantage, away_rating
        )

        if home_goals > away_goals:
            actual_home = 1.0
        elif home_goals == away_goals:
            actual_home = 0.5
        else:
            actual_home = 0.0

        goal_diff = home_goals - away_goals
        multiplier = self.margin_multiplier(goal_diff)
        k = self.config.k_factor * multiplier

        new_home_rating = home_rating + k * (actual_home - expected_home)
        new_away_rating = away_rating + k * ((1 - actual_home) - (1 - expected_home))

        self.ratings[home_team] = new_home_rating
        self.ratings[away_team] = new_away_rating

        return home_rating, away_rating

    def add_ratings_to_matches(self, matches: pd.DataFrame) -> pd.DataFrame:

        matches = matches.copy()
        home_elo_before = []
        away_elo_before = []

        for row in matches.itertuples(index=False):
            home_before, away_before = self.process_match(
                row.home_team, row.away_team, row.home_goals, row.away_goals
            )
            home_elo_before.append(home_before)
            away_elo_before.append(away_before)

        matches["home_elo"] = home_elo_before
        matches["away_elo"] = away_elo_before
        matches["elo_diff"] = matches["home_elo"] - matches["away_elo"]
        return matches

