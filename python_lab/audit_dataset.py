from __future__ import annotations
import argparse
import pandas as pd

REQUIRED = ["date", "league", "home_team", "away_team", "home_goals", "away_goals"]
PROP_COLS = ["home_corners", "away_corners", "home_shots", "away_shots", "home_yellow", "away_yellow"]

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="../data/unified_intl_matches.csv")
    args = ap.parse_args()
    df = pd.read_csv(args.data)
    print(f"rows={len(df)} cols={len(df.columns)}")
    missing_required = [c for c in REQUIRED if c not in df.columns]
    print("missing_required=", missing_required)
    for c in REQUIRED:
        if c in df.columns:
            print(f"null_{c}=", int(df[c].isna().sum()))
    if "date" in df.columns:
        print("min_date=", df["date"].min(), "max_date=", df["date"].max())
    if all(c in df.columns for c in ["date", "home_team", "away_team"]):
        dups = df.duplicated(["date", "home_team", "away_team"], keep=False).sum()
        print("duplicate_date_home_away_rows=", int(dups))
    for c in PROP_COLS:
        if c in df.columns:
            print(f"coverage_{c}=", round(100 * df[c].notna().mean(), 1), "%")

if __name__ == "__main__":
    main()
