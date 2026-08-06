"""
models.py

Baseline, Logistic Regression, Poisson goals model, and Random Forest.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, PoissonRegressor
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

FEATURE_COLUMNS = [
    "elo_diff",
    "home_form_ppg", "away_form_ppg",
    "home_form_gf", "away_form_gf",
    "home_form_ga", "away_form_ga",
    "home_rest_days", "away_rest_days",
    "h2h_home_win_rate",
    "day_of_week",
]

OUTCOME_ORDER = ["A", "D", "H"]


def prepare_features(matches: pd.DataFrame) -> pd.DataFrame:
    df = matches.copy()
    form_cols = ["home_form_ppg", "away_form_ppg", "home_form_gf",
                 "away_form_gf", "home_form_ga", "away_form_ga"]
    for col in form_cols:
        df[col] = df[col].fillna(df[col].mean())
    for col in ["home_rest_days", "away_rest_days"]:
        df[col] = df[col].fillna(df[col].median())
    df["h2h_home_win_rate"] = df["h2h_home_win_rate"].fillna(0.5)
    return df


def get_X_y(matches: pd.DataFrame):
    X = matches[FEATURE_COLUMNS]
    y = matches["result"]
    return X, y


class BaselineModel:

    def __init__(self):
        self.class_priors = None

    def fit(self, X, y):
        counts = pd.Series(y).value_counts(normalize=True)
        self.class_priors = np.array([counts.get(c, 0.0) for c in OUTCOME_ORDER])
        return self

    def predict_proba(self, X):
        n = len(X)
        return np.tile(self.class_priors, (n, 1))


class LogisticModel:
    def __init__(self):
        self.scaler = StandardScaler()
        self.clf = LogisticRegression(max_iter=1000)

    def fit(self, X, y):
        X_scaled = self.scaler.fit_transform(X)
        self.clf.fit(X_scaled, y)
        return self

    def predict_proba(self, X):
        X_scaled = self.scaler.transform(X)
        raw_probs = self.clf.predict_proba(X_scaled)
        return _reorder_columns(raw_probs, self.clf.classes_)


class PoissonGoalsModel:
    def __init__(self, max_goals: int = 8):
        self.max_goals = max_goals
        self.scaler = StandardScaler()
        self.home_model = PoissonRegressor(max_iter=1000)
        self.away_model = PoissonRegressor(max_iter=1000)

    def fit(self, X, y_home_goals, y_away_goals):
        X_scaled = self.scaler.fit_transform(X)
        self.home_model.fit(X_scaled, y_home_goals)
        self.away_model.fit(X_scaled, y_away_goals)
        return self

    def _score_distribution(self, lam_home: float, lam_away: float) -> np.ndarray:
        from scipy.stats import poisson
        home_probs = poisson.pmf(np.arange(self.max_goals + 1), lam_home)
        away_probs = poisson.pmf(np.arange(self.max_goals + 1), lam_away)
        return np.outer(home_probs, away_probs)

    def predict_proba(self, X) -> np.ndarray:
        X_scaled = self.scaler.transform(X)
        lam_home = self.home_model.predict(X_scaled)
        lam_away = self.away_model.predict(X_scaled)

        n = len(X)
        probs = np.zeros((n, 3))
        for i in range(n):
            grid = self._score_distribution(lam_home[i], lam_away[i])
            away_win = np.tril(grid, k=-1).sum()
            draw = np.trace(grid)
            home_win = np.triu(grid, k=1).sum()
            probs[i] = [away_win, draw, home_win]

        probs = probs / probs.sum(axis=1, keepdims=True)
        return probs

    def predict_expected_goals(self, X):
        X_scaled = self.scaler.transform(X)
        return self.home_model.predict(X_scaled), self.away_model.predict(X_scaled)


class RandomForestModel:
    def __init__(self, n_estimators: int = 300, max_depth: int = 8, random_state: int = 42):
        self.clf = RandomForestClassifier(
            n_estimators=n_estimators, max_depth=max_depth,
            random_state=random_state, min_samples_leaf=5,
        )

    def fit(self, X, y):
        self.clf.fit(X, y)
        return self

    def predict_proba(self, X):
        raw_probs = self.clf.predict_proba(X)
        return _reorder_columns(raw_probs, self.clf.classes_)

    def feature_importances(self, feature_names=FEATURE_COLUMNS):
        return pd.Series(self.clf.feature_importances_, index=feature_names).sort_values(ascending=False)


def _reorder_columns(probs: np.ndarray, classes: np.ndarray) -> np.ndarray:
    out = np.zeros_like(probs)
    for i, cls in enumerate(classes):
        out[:, OUTCOME_ORDER.index(cls)] = probs[:, i]
    return out