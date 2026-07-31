
import numpy as np
from sklearn.metrics import accuracy_score, log_loss

from src.data_loader import load_matches
from src.elo import EloRatingSystem
from src.features import build_features
from src.models import (
    prepare_features, get_X_y, FEATURE_COLUMNS, OUTCOME_ORDER,
    BaselineModel, LogisticModel, PoissonGoalsModel, RandomForestModel,
)


def chronological_split(matches, test_fraction: float = 0.2):

    matches = matches.sort_values("date").reset_index(drop=True)
    split_idx = int(len(matches) * (1 - test_fraction))
    train = matches.iloc[:split_idx]
    test = matches.iloc[split_idx:]
    return train, test


def evaluate(name, y_true, probs):
    preds = [OUTCOME_ORDER[i] for i in np.argmax(probs, axis=1)]
    acc = accuracy_score(y_true, preds)
    # log_loss needs probabilities in the same class order as its `labels` arg.
    ll = log_loss(y_true, probs, labels=OUTCOME_ORDER)
    print(f"{name:20s}  accuracy={acc:.3f}   log_loss={ll:.3f}")
    return acc, ll


def main():
    print("Loading matches from data/raw/ ...")
    matches = load_matches()
    print(f"  {len(matches)} matches, {matches['date'].min().date()} to {matches['date'].max().date()}")

    print("Computing Elo ratings ...")
    matches = EloRatingSystem().add_ratings_to_matches(matches)

    print("Building features ...")
    matches = build_features(matches)
    matches = prepare_features(matches)

    print("Splitting chronologically (last 20% of matches = test set) ...")
    train, test = chronological_split(matches, test_fraction=0.2)
    print(f"  train: {len(train)} matches ({train['date'].min().date()} to {train['date'].max().date()})")
    print(f"  test:  {len(test)} matches ({test['date'].min().date()} to {test['date'].max().date()})")

    X_train, y_train = get_X_y(train)
    X_test, y_test = get_X_y(test)

    print("\nTraining and evaluating models ...")
    print("-" * 60)

    baseline = BaselineModel().fit(X_train, y_train)
    evaluate("Baseline (home win)", y_test, baseline.predict_proba(X_test))

    logit = LogisticModel().fit(X_train, y_train)
    evaluate("Logistic Regression", y_test, logit.predict_proba(X_test))

    poisson_model = PoissonGoalsModel().fit(
        X_train, train["home_goals"], train["away_goals"]
    )
    evaluate("Poisson (goals)", y_test, poisson_model.predict_proba(X_test))

    rf = RandomForestModel().fit(X_train, y_train)
    evaluate("Random Forest", y_test, rf.predict_proba(X_test))

    print("-" * 60)

    # Compare against bookmaker odds, if available -- this is the real test
    # of whether the model has found anything the market hasn't already priced in.
    if "odds_home" in test.columns and test["odds_home"].notna().any():
        odds_probs = _odds_to_probs(test)
        valid = ~np.isnan(odds_probs).any(axis=1)
        if valid.sum() > 0:
            evaluate("Bookmaker odds", y_test[valid], odds_probs[valid])

    print("\nRandom Forest feature importances:")
    print(rf.feature_importances())


def _odds_to_probs(test):

    raw = 1.0 / test[["odds_away", "odds_draw", "odds_home"]].to_numpy()
    return raw / raw.sum(axis=1, keepdims=True)


if __name__ == "__main__":
    main()