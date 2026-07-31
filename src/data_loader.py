"""
Loads and cleans Prem League match data from the CSVs in data/raw/

"""

from pathlib import Path
import pandas as pd

KEEP_COLUMNS = {
    "Date": "date",
    "HomeTeam": "home_team",
    "AwayTeam": "away_team",
    "FTHG": "home_goals",
    "FTAG": "away_goals",
    "FTR": "result",
    "HS": "home_shots",
    "AS": "away_shots",
    "HST": "home_shots_target",
    "AST": "away_shots_target",
    "HC": "home_corners",
    "AC": "away_corners",
    "HY": "home_yellows",
    "AY": "away_yellows",
    "HR": "home_reds",
    "AR": "away_reds",


    "B365H": "odds_home",
    "B365D": "odds_draw",
    "B365A": "odds_away",
}

def _clean_file(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    present = {k: v for k, v in KEEP_COLUMNS.items() if k in df.columns}
    df = df[list(present.keys())].rename(columns=present)

    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["date", "home_team", "away_team", "result"])

    df["season_file"] = path.stem
    return df

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw"


def load_matches(raw_dir: str | Path = None) -> pd.DataFrame:

    raw_dir = Path(raw_dir) if raw_dir is not None else DEFAULT_RAW_DIR
    csv_files = sorted(raw_dir.glob("*.csv"))

    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {raw_dir.resolve()}.")

    frames = [_clean_file(f) for f in csv_files]
    matches = pd.concat(frames, ignore_index=True)
    matches = matches.sort_values("date").reset_index(drop=True)

    for col in ["home_team", "away_team"]:
        matches[col] = matches[col].str.strip()

    return matches

if __name__ == "__main__":

    #test

    matches = load_matches()
    print(f"Loaded {len(matches)} matches from {matches['date'].min().date()} "f"to {matches['date'].max().date()}")
    #print(matches.head())