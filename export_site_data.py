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


def compute_elo_history(matches, top_n_teams: int = 8):
    """
    Re-walks the matches chronologically, recording the POST-match rating
    at every step for every team. Then aligns all teams onto a single
    shared sequence of match dates (forward-filling each team's rating
    between its own matches), so the frontend can plot them on a plain
    category axis -- no JS date-time adapter dependency required, which
    is a common source of silent rendering failures in Chart.js.
    """
    elo = EloRatingSystem(EloConfig())
    per_team_series = {}  # team -> {date_str: rating}

    all_dates = sorted(matches["date"].dt.strftime("%Y-%m-%d").unique())

    for row in matches.itertuples(index=False):
        elo.process_match(row.home_team, row.away_team, row.home_goals, row.away_goals)
        date_str = row.date.strftime("%Y-%m-%d")
        per_team_series.setdefault(row.home_team, {})[date_str] = round(elo.get_rating(row.home_team), 1)
        per_team_series.setdefault(row.away_team, {})[date_str] = round(elo.get_rating(row.away_team), 1)

    final_ratings = {team: list(series.values())[-1] for team, series in per_team_series.items()}
    top_teams = sorted(final_ratings, key=final_ratings.get, reverse=True)[:top_n_teams]

    # Forward-fill each top team's rating across the shared date axis so
    # every series has a value (or null before that team's first match)
    # at every date in all_dates -- makes the datasets directly alignable
    # in the chart without any date parsing on the JS side.
    aligned = {}
    for team in top_teams:
        series = per_team_series[team]
        values = []
        last = None
        for d in all_dates:
            if d in series:
                last = series[d]
            values.append(last)
        aligned[team] = values

    return {"dates": all_dates, "series": aligned}


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
    elo_history = compute_elo_history(matches)

    print("Writing JSON to docs/data/ ...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_DIR / "results.json", "w") as f:
        json.dump(results, f, indent=2)

    with open(OUTPUT_DIR / "feature_importance.json", "w") as f:
        json.dump(feature_importance, f, indent=2)

    with open(OUTPUT_DIR / "elo_history.json", "w") as f:
        json.dump(elo_history, f, indent=2)

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