"""
export_site_data.py

Runs the full pipeline on real data in data/raw/ and writes the results
out as JSON files that docs/index.html reads to render charts. Run this
any time you update your data or models, then commit the refreshed
docs/data/*.json files.

Run from the project root:
    python export_site_data.py
"""

import json
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, log_loss

from src.data_loader import load_matches
from src.elo import EloRatingSystem, EloConfig
from src.features import build_features
from src.models import (
    prepare_features, get_X_y, FEATURE_COLUMNS, OUTCOME_ORDER,
    BaselineModel, LogisticModel, PoissonGoalsModel, RandomForestModel,
)
from main import chronological_split, _odds_to_probs

OUTPUT_DIR = Path(__file__).resolve().parent / "docs" / "data"


def compute_model_results(train, test):
    X_train, y_train = get_X_y(train)
    X_test, y_test = get_X_y(test)

    results = []

    def add_result(name, probs, y_true=y_test):
        preds = [OUTCOME_ORDER[i] for i in np.argmax(probs, axis=1)]
        acc = accuracy_score(y_true, preds)
        ll = log_loss(y_true, probs, labels=OUTCOME_ORDER)
        results.append({"name": name, "accuracy": round(float(acc), 4), "log_loss": round(float(ll), 4)})

    baseline = BaselineModel().fit(X_train, y_train)
    add_result("Baseline (home win)", baseline.predict_proba(X_test))

    logit = LogisticModel().fit(X_train, y_train)
    add_result("Logistic Regression", logit.predict_proba(X_test))

    poisson_model = PoissonGoalsModel().fit(X_train, train["home_goals"], train["away_goals"])
    add_result("Poisson (goals)", poisson_model.predict_proba(X_test))

    rf = RandomForestModel().fit(X_train, y_train)
    add_result("Random Forest", rf.predict_proba(X_test))

    if "odds_home" in test.columns and test["odds_home"].notna().any():
        odds_probs = _odds_to_probs(test)
        valid = ~np.isnan(odds_probs).any(axis=1)
        if valid.sum() > 0:
            add_result("Bookmaker odds", odds_probs[valid], y_test[valid])

    feature_importance = [
        {"feature": name, "importance": round(float(val), 4)}
        for name, val in rf.feature_importances().items()
    ]

    return results, feature_importance


def _season_label(date_str: str) -> str:
    """
    Premier League seasons run August -> May. Given a match date, returns
    a label like '2021/22' for the season it falls in (games in
    Jul-Dec belong to the season starting that year; games in Jan-Jun
    belong to the season that started the previous year).
    """
    year, month = int(date_str[:4]), int(date_str[5:7])
    start_year = year if month >= 7 else year - 1
    return f"{start_year}/{str(start_year + 1)[-2:]}"


def _season_boundaries(dates: list[str]) -> list[dict]:
    """
    Returns the index of the first match date in each season, paired with
    that season's label -- e.g. [{"index": 0, "label": "2021/22"},
    {"index": 380, "label": "2022/23"}, ...]. Used by the frontend to draw
    x-axis ticks at season boundaries instead of arbitrary month ticks, so
    it's easy to see where one season ends and the next begins.
    """
    boundaries = []
    last_label = None
    for i, d in enumerate(dates):
        label = _season_label(d)
        if label != last_label:
            boundaries.append({"index": i, "label": label})
            last_label = label
    return boundaries


def compute_elo_history(matches, top_n_teams: int = None):
    """
    Re-walks the matches chronologically, recording the POST-match rating
    at every step for every team. Then aligns all teams onto a single
    shared sequence of match dates (forward-filling each team's rating
    between its own matches), so the frontend can plot them on a plain
    category axis -- no JS date-time adapter dependency required, which
    is a common source of silent rendering failures in Chart.js.

    top_n_teams=None returns every team (needed so the team-picker dropdown
    can show any team's history, not just the top few).
    """
    elo = EloRatingSystem(EloConfig())
    per_team_series = {}  # team -> {date_str: rating}

    all_dates = sorted(matches["date"].dt.strftime("%Y-%m-%d").unique())
    season_boundaries = _season_boundaries(all_dates)

    for row in matches.itertuples(index=False):
        elo.process_match(row.home_team, row.away_team, row.home_goals, row.away_goals)
        date_str = row.date.strftime("%Y-%m-%d")
        per_team_series.setdefault(row.home_team, {})[date_str] = round(elo.get_rating(row.home_team), 1)
        per_team_series.setdefault(row.away_team, {})[date_str] = round(elo.get_rating(row.away_team), 1)

    final_ratings = {team: list(series.values())[-1] for team, series in per_team_series.items()}
    ranked_teams = sorted(final_ratings, key=final_ratings.get, reverse=True)
    teams_to_include = ranked_teams if top_n_teams is None else ranked_teams[:top_n_teams]

    # Forward-fill each team's rating across the shared date axis so
    # every series has a value (or null before that team's first match)
    # at every date in all_dates -- makes the datasets directly alignable
    # in the chart without any date parsing on the JS side.
    aligned = {}
    for team in teams_to_include:
        series = per_team_series[team]
        values = []
        last = None
        for d in all_dates:
            if d in series:
                last = series[d]
            values.append(last)
        aligned[team] = values

    return (
        {"dates": all_dates, "series": aligned, "season_boundaries": season_boundaries},
        final_ratings,
        ranked_teams,
    )


def compute_team_profiles(matches, final_ratings, ranked_teams, n_recent: int = 5):
    """
    Per-team summary for the team-picker view: current Elo rank, rating,
    and their last N results (opponent, venue, score, W/D/L) in reverse
    chronological order (most recent first).
    """
    rank_by_team = {team: i + 1 for i, team in enumerate(ranked_teams)}
    profiles = {}

    for team in ranked_teams:
        is_home = matches["home_team"] == team
        is_away = matches["away_team"] == team
        team_matches = matches[is_home | is_away].sort_values("date")

        recent = []
        for row in team_matches.tail(n_recent).iloc[::-1].itertuples(index=False):
            if row.home_team == team:
                opponent, venue = row.away_team, "H"
                gf, ga = row.home_goals, row.away_goals
            else:
                opponent, venue = row.home_team, "A"
                gf, ga = row.away_goals, row.home_goals

            if gf > ga:
                result = "W"
            elif gf == ga:
                result = "D"
            else:
                result = "L"

            recent.append({
                "date": row.date.strftime("%Y-%m-%d"),
                "opponent": opponent,
                "venue": venue,
                "score": f"{gf}-{ga}",
                "result": result,
            })

        profiles[team] = {
            "rank": rank_by_team[team],
            "elo": round(final_ratings[team], 1),
            "matches_played": len(team_matches),
            "recent_form": recent,
        }

    return profiles


def main():
    print("Loading matches ...")
    matches = load_matches()

    print("Computing Elo ratings ...")
    matches = EloRatingSystem().add_ratings_to_matches(matches)

    print("Building features ...")
    matches = build_features(matches)
    matches = prepare_features(matches)

    print("Splitting and training models ...")
    train, test = chronological_split(matches, test_fraction=0.2)
    results, feature_importance = compute_model_results(train, test)

    print("Computing Elo history for chart ...")
    elo_history_all, final_ratings, ranked_teams = compute_elo_history(matches, top_n_teams=None)

    # Overview chart on the main page stays uncluttered (top 8 only).
    # The team-picker dropdown uses elo_history_all, which has everyone.
    overview_teams = ranked_teams[:8]
    elo_history_overview = {
        "dates": elo_history_all["dates"],
        "series": {t: elo_history_all["series"][t] for t in overview_teams},
        "season_boundaries": elo_history_all["season_boundaries"],
    }

    print("Computing team profiles ...")
    team_profiles = compute_team_profiles(matches, final_ratings, ranked_teams)

    print("Writing JSON to docs/data/ ...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_DIR / "results.json", "w") as f:
        json.dump(results, f, indent=2)

    with open(OUTPUT_DIR / "feature_importance.json", "w") as f:
        json.dump(feature_importance, f, indent=2)

    with open(OUTPUT_DIR / "elo_history.json", "w") as f:
        json.dump(elo_history_overview, f, indent=2)

    with open(OUTPUT_DIR / "elo_history_all.json", "w") as f:
        json.dump(elo_history_all, f, indent=2)

    with open(OUTPUT_DIR / "team_profiles.json", "w") as f:
        json.dump(team_profiles, f, indent=2)

    with open(OUTPUT_DIR / "summary.json", "w") as f:
        json.dump({
            "num_matches": len(matches),
            "date_range": [matches["date"].min().strftime("%Y-%m-%d"),
                            matches["date"].max().strftime("%Y-%m-%d")],
            "num_teams": int(matches["home_team"].nunique()),
            "train_size": len(train),
            "test_size": len(test),
        }, f, indent=2)

    print("Done. Files written:")
    for f in sorted(OUTPUT_DIR.glob("*.json")):
        print(f"  {f}")


if __name__ == "__main__":
    main()
