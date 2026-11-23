# Capstone: from raw data to interview-ready conclusions

Data: `data/users.csv`, `data/events.csv`, `data/capstone.db`.

This part deliberately comes without reference answers; it is the final check.

## Part 1 — Data audit
1. Row count, column count, types, missing values;
2. Uniqueness of user_id;
3. Date range;
4. Treatment share;
5. Country/channel summary.

## Part 2 — SQL
1. Users, conversion rate and revenue for each acquisition channel;
2. Daily active users;
3. Each user's first event;
4. Average events per user for treatment and control;
5. Weekly conversion for each channel, ranked with a window function.

## Part 3 — Experiment
1. Treatment/control conversion difference;
2. 95% CI / test;
3. Revenue outcome;
4. Sample-ratio check;
5. Segment heterogeneity;
6. Separate confirmatory from exploratory findings.

## Part 4 — Predictive modeling
Predict `converted`: split → preprocessing → logistic baseline → tree model → CV → metric → calibration/threshold → error analysis.

## Part 5 — Communication
Produce a 5-sentence executive summary, a 2-minute verbal walkthrough and a list of limitations.

## Passing bar
Given a new, unfamiliar dataset of the same kind, you can still run the whole workflow on your own.
