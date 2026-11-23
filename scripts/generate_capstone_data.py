from pathlib import Path
import numpy as np, pandas as pd, sqlite3
OUT = Path(__file__).resolve().parents[1] / "data"
OUT.mkdir(exist_ok=True)
rng = np.random.default_rng(2027)
n = 8000
u = pd.DataFrame({
    "user_id": np.arange(1,n+1),
    "country": rng.choice(["US","CA","UK","DE"], n, p=[.65,.10,.15,.10]),
    "age": np.clip(rng.normal(36,12,n).round(),18,80),
    "acq_channel": rng.choice(["organic","search","social","referral"], n, p=[.35,.30,.20,.15])
})
u["signup_date"] = pd.Timestamp("2026-01-01") + pd.to_timedelta(rng.integers(0,180,n), unit="D")
u["treatment"] = rng.binomial(1,.5,n)
logit = -2.2 + .018*(u["age"]-35) + .35*(u["acq_channel"]=="organic").astype(float) + .18*u["treatment"]
u["converted"] = rng.binomial(1, 1/(1+np.exp(-logit)))
br = rng.gamma(2.2,22,n)
u["revenue_30d"] = np.where(u["converted"].eq(1), br*(1+.06*u["treatment"]), 0)
u.loc[rng.choice(n,250,replace=False),"age"] = np.nan
rows=[]
for uid, signup, conv, tr in u[["user_id","signup_date","converted","treatment"]].itertuples(index=False):
    m=int(rng.poisson(6+3*conv+tr))
    for d in np.sort(rng.integers(0,31,max(m,1))):
        rows.append((uid, signup+pd.Timedelta(days=int(d)), rng.choice(["view","click","search","purchase"], p=[.45,.30,.20,.05])))
e=pd.DataFrame(rows,columns=["user_id","event_date","event_type"])
u.to_csv(OUT/"users.csv",index=False)
e.to_csv(OUT/"events.csv",index=False)
db=OUT/"capstone.db"
if db.exists(): db.unlink()
con=sqlite3.connect(db)
u.to_sql("users",con,index=False,if_exists="replace")
e.to_sql("events",con,index=False,if_exists="replace")
con.close()
print("Generated:", OUT)
