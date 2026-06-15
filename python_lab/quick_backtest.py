from __future__ import annotations
import argparse, math
from collections import defaultdict
import pandas as pd

def canon(x: str) -> str:
    m = {
        "United States": "USA", "United States of America": "USA", "U.S.A.": "USA",
        "Czech Republic": "Czechia", "Turkey": "Turkiye", "Cabo Verde": "Cape Verde",
        "Cape Verde Islands": "Cape Verde", "Ivory Coast": "Côte d'Ivoire",
        "DR Congo": "Congo DR", "Curacao": "Curaçao", "Korea Republic": "South Korea",
    }
    return m.get(str(x).strip(), str(x).strip())

def poisson(k: int, lam: float) -> float:
    p = math.exp(-lam)
    for i in range(k):
        p *= lam / (i + 1)
    return p

def train(df: pd.DataFrame):
    gf = defaultdict(float); ga = defaultdict(float); n = defaultdict(float)
    total_goals = 0.0
    for _, r in df.iterrows():
        h, a = canon(r.home_team), canon(r.away_team)
        hg, ag = float(r.home_goals), float(r.away_goals)
        gf[h] += hg; ga[h] += ag; n[h] += 1
        gf[a] += ag; ga[a] += hg; n[a] += 1
        total_goals += hg + ag
    avg = total_goals / max(1, 2 * len(df))
    return gf, ga, n, avg

def predict(model, h: str, a: str):
    gf, ga, n, avg = model
    h, a = canon(h), canon(a)
    hm, am = max(1, n[h]), max(1, n[a])
    h_att = min(3.2, max(0.35, (gf[h]/hm) / avg))
    h_def = min(3.2, max(0.35, (ga[h]/hm) / avg))
    a_att = min(3.2, max(0.35, (gf[a]/am) / avg))
    a_def = min(3.2, max(0.35, (ga[a]/am) / avg))
    lh = min(4.5, max(0.05, avg * h_att * math.sqrt(a_def)))
    la = min(4.5, max(0.05, avg * a_att * math.sqrt(h_def)))
    H=D=A=O25=BTTS=0.0
    best=(0,0,0.0)
    for i in range(8):
        for j in range(8):
            p = poisson(i, lh)*poisson(j, la)
            if i>j: H+=p
            elif i==j: D+=p
            else: A+=p
            if i+j>=3: O25+=p
            if i>0 and j>0: BTTS+=p
            if p>best[2]: best=(i,j,p)
    s=H+D+A
    return {"H":H/s,"D":D/s,"A":A/s,"O25":O25,"BTTS":BTTS,"xg":(lh,la),"score":best[:2]}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="../data/unified_intl_matches.csv")
    ap.add_argument("--home")
    ap.add_argument("--away")
    args = ap.parse_args()
    df = pd.read_csv(args.data).sort_values("date")
    model = train(df)
    if args.home and args.away:
        p = predict(model, args.home, args.away)
        print(args.home, "vs", args.away, p)
        return
    correct = o25c = n = 0
    # In-sample sanity. For real quality use expanding-window by date.
    for _, r in df.iterrows():
        p = predict(model, r.home_team, r.away_team)
        pick = max(["H","D","A"], key=lambda k: p[k])
        actual = "H" if r.home_goals > r.away_goals else "A" if r.home_goals < r.away_goals else "D"
        correct += pick == actual
        o25c += (p["O25"] >= .5) == ((r.home_goals + r.away_goals) >= 3)
        n += 1
    print(f"in_sample_1x2_accuracy={correct/n:.3f} ({correct}/{n})")
    print(f"in_sample_over25_accuracy={o25c/n:.3f} ({o25c}/{n})")

if __name__ == "__main__":
    main()
