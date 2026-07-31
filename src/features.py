import pandas as pd
import numpy as np

FORM_WINDOW = 5
H2H_WINDOW = 5

def to_long_format(matches: pd.DataFrame) -> pd.DataFrame:
    home_rows = pd.DataFrame({
        "match_idx": matches.index,
        "date": matches["date"],
        "team": matches["home_team"],
        "opponent": matches["away_team"],
        "is_home": True,
        "goals_for": matches["home_goals"],
        "goals_against": matches["away_goals"],
    })
    away_rows = pd.DataFrame({
        "match_idx": matches.index,
        "date": matches["date"],
        "team": matches["away_team"],
        "opponent": matches["home_team"],
        "is_home": False,
        "goals_for": matches["away_goals"],
        "goals_against": matches["away_goals"],
    })

    long_df = pd.concat([home_rows, away_rows], ignore_index=True)
    long_df["points"] = np.select([
        long_df["goals_for"] > long_df["goals_against"],
        long_df["goals_for"] == long_df["goals_against"]],
        [3,1], default=0,)
    long_df = long_df.sort_values(["team", "date"]). reset_index(drop=True)
    return long_df

def add_rolling_form(matches: pd.DataFrame, window:int = FORM_WINDOW) -> pd.DataFrame:
    matches = matches.copy()
    long_df = to_long_format(matches)

    grouped = long_df.groupby("team")
    for col, out_col in [("points", "form_ppg"), ("goals_for", "form_gf"), ("goals_against", "form_ga")]:
        long_df[out_col] = grouped[col].transform(
            lambda s: s.shift(1).rolling(window, min_periods=1).mean()

        )

    home_feats = long_df[long_df["is_home"]].set_index("match_idx")[
        ["form_ppg", "form_gf", "form_ga"]
    ].rename(columns={"form_ppg": "home_form_ppg", "form_gf": "home_form_gf","form_ga": "home_form_ga"})

    away_feats = long_df[~long_df["is_home"]].set_index("match_idx")[["form_ppg", "form_gf", "form_ga"]
    ].rename(columns={"form_ppg": "away_form_ppg", "form_gf": "away_form_gf", "form_ga": "away_form_ga"})

    matches = matches.join(home_feats).join(away_feats)
    return matches


def add_rest_days(matches: pd.DataFrame) -> pd.DataFrame:

    matches = matches.copy()
    long_df = to_long_format(matches)
    long_df["prev_date"] = long_df.groupby("team")["date"].shift(1)
    long_df["rest_days"] = (long_df["date"] - long_df["prev_date"]).dt.days

    home_rest = long_df[long_df["is_home"]].set_index("match_idx")[["rest_days"]].rename(
        columns={"rest_days": "home_rest_days"})
    away_rest = long_df[~long_df["is_home"]].set_index("match_idx")[["rest_days"]].rename(
        columns={"rest_days": "away_rest_days"})

    matches = matches.join(home_rest).join(away_rest)
    return matches


def add_head_to_head(matches: pd.DataFrame, window: int = H2H_WINDOW) -> pd.DataFrame:

    matches = matches.copy()
    matches["pair_key"] = matches.apply(
        lambda r: tuple(sorted([r["home_team"], r["away_team"]])), axis=1
    )

    h2h_rates = []
    # Walk chronologically per pair, looking back at prior meetings only.
    for pair_key, group in matches.groupby("pair_key"):
        group = group.sort_values("date")
        history = []  # list of (winner) from past meetings in this pair
        for idx, row in group.iterrows():
            if len(history) == 0:
                rate = np.nan
            else:
                recent = history[-window:]
                rate = sum(1 for w in recent if w == row["home_team"]) / len(recent)
            h2h_rates.append((idx, rate))

            if row["result"] == "H":
                winner = row["home_team"]
            elif row["result"] == "A":
                winner = row["away_team"]
            else:
                winner = None  # draw -- no winner to record
            if winner is not None:
                history.append(winner)

    h2h_df = pd.DataFrame(h2h_rates, columns=["idx", "h2h_home_win_rate"]).set_index("idx")
    matches = matches.join(h2h_df)
    matches = matches.drop(columns=["pair_key"])
    return matches


def add_calendar_features(matches: pd.DataFrame) -> pd.DataFrame:

    matches = matches.copy()
    matches["day_of_week"] = matches["date"].dt.dayofweek
    if "time" in matches.columns:
        matches["match_hour"] = pd.to_datetime(
            matches["time"], format="%H:%M", errors="coerce"
        ).dt.hour
    return matches


def build_features(matches: pd.DataFrame) -> pd.DataFrame:

    matches = matches.sort_values("date").reset_index(drop=True)
    matches = add_rolling_form(matches)
    matches = add_rest_days(matches)
    matches = add_head_to_head(matches)
    matches = add_calendar_features(matches)
    return matches
