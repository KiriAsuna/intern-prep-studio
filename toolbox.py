# -*- coding: utf-8 -*-
"""Exercise helpers derived from the reference answer.

- `answer_tools`: the functions / methods / syntax an answer uses, in order, with a one-line reminder each
  (the "🧰 Tools for this problem" fold: what to reach for, not how to put it together);
- `first_taught`: the lesson where each tool is first demonstrated, so a reminder can point back to it;
- `skeleton`: a fill-in version of the answer (the "🪜 Fill-in version" fold), a step between a blank editor and the answer.
"""
from __future__ import annotations

import ast
import io
import json
import re
import tokenize
from pathlib import Path

# key -> (usage, note). Keys match what _py_keys produces: ".method", "func(", "kw=", or a syntax name; SQL uses upper-case keywords.
PY = {
    # ---- Python basics
    ".append": ("lst.append(x)", "Add one element to the end of a list, in place. R: `v <- c(v, x)`"),
    ".extend": ("lst.extend(other)", "Append each element of another list (`append` would add the whole list as one element)"),
    ".pop": ("lst.pop()", "Remove and return the last element (stack pop); `lst.pop(0)` removes the first"),
    ".popleft": ("dq.popleft()", "Take one item from the left end of a deque (queue dequeue, O(1))"),
    ".remove": ("s.remove(x)", "Remove the value x from a set / list (error if it is missing)"),
    ".add": ("s.add(x)", "Add an element to a set"),
    ".get": ("d.get(k, default)", "Look up k in a dict; returns the default instead of raising if k is missing"),
    ".items": ("for k, v in d.items():", "Loop over a dict's keys and values together"),
    ".values": ("d.values()", "All values of a dict (on a DataFrame, `.values` is the underlying array)"),
    ".keys": ("d.keys()", "All keys of a dict"),
    ".join": ('", ".join(words)', "Join a list of strings with a separator. R: `paste(words, collapse = \", \")`"),
    ".split": ('s.split(",")', "Split into a list on a separator. R: `strsplit()`"),
    ".strip": ("s.strip()", "Trim whitespace at both ends. R: `trimws()`; for a whole column use `s.str.strip()`"),
    ".lower": ("s.lower()", "Lower case. R: `tolower()`"),
    ".upper": ("s.upper()", "Upper case. R: `toupper()`"),
    ".isalnum": ("ch.isalnum()", "Is it a letter or digit"),
    ".copy": ("b = a.copy()", "Make a copy so that changing b leaves a alone (same for list / dict / DataFrame)"),
    ".count": ("lst.count(x) / s.count()", "list: how many times x occurs; pandas: number of non-missing values (often used after groupby)"),
    "sorted(": ("sorted(xs, key=..., reverse=True)", "Return a new sorted list; the original is unchanged. R: `sort()`"),
    ".sort": ("xs.sort()", "Sort in place; returns nothing"),
    "key=": ("key=lambda t: t[1]", "What to sort / compare by: compute a value per element and compare those"),
    "reverse=": ("reverse=True", "Largest first"),
    "enumerate(": ("for i, x in enumerate(xs):", "Get the index (from 0) and the element together. R: `seq_along()`"),
    "start=": ("enumerate(xs, start=1)", "Count the index from 1"),
    "zip(": ("for a, b in zip(xs, ys):", "Walk two sequences in lockstep"),
    "range(": ("range(n) / range(a, b, step)", "0 to n-1; a to b-1 (right end excluded)"),
    "abs(": ("abs(x)", "Absolute value"),
    "round(": ("round(x, 2)", "Round to 2 decimals"),
    "int(": ("int(x)", "Convert to an integer"),
    "float(": ("float(x)", "Convert to a float; `float(\"inf\")` is positive infinity"),
    "str(": ("str(x)", "Convert to a string"),
    "list(": ("list(x)", "Convert to a list"),
    "set(": ("set(xs)", "Convert to a set: removes duplicates, O(1) `in` checks"),
    "dict(": ("dict()", "Create a dict"),
    "sum(": ("sum(xs)", "Sum"),
    "max(": ("max(a, b) / max(xs)", "Maximum; also accepts `key=`"),
    "min(": ("min(a, b) / min(xs)", "Minimum"),
    "isinstance(": ("isinstance(x, list)", "Check whether x is of a given type"),
    "lambda": ("lambda x: x * 2", "A one-line function. R: `function(x) x * 2`"),
    "f-string": ('f"{n} in total"', "Embed variables in a string with `{}`. R: `glue()` / `sprintf()`"),
    "comprehension": ("[f(x) for x in xs if cond]", "Comprehension: build a list / dict / set in one line"),
    "try": ("try: ... except ValueError: ...", "On an error, jump to the except block. R: `tryCatch()`"),
    "while": ("while cond:", "Loop while the condition is true; remember to update the variable inside"),
    "x if c else y": ("a if cond else b", "One-line if-else. R: `if (cond) a else b`"),
    "[::step]": ("s[::-1]", "Reversed; `s[::2]` takes every other element"),
    "Counter(": ("Counter(xs)", "Count how often each element occurs, as a dict. R: `table()` (`from collections import Counter`)"),
    ".most_common": ("cnt.most_common(k)", "The k most frequent, as a list of (element, count)"),
    "defaultdict(": ("defaultdict(list)", "Missing keys get a default value (empty list / 0), so no `if k not in d`"),
    "deque(": ("deque([start])", "Double-ended queue, O(1) at both ends; used for BFS (`from collections import deque`)"),
    ".heappush": ("heapq.heappush(h, x)", "Push onto a min-heap"),
    ".heappop": ("heapq.heappop(h)", "Pop the smallest item from the heap"),
    ".bisect_left": ("bisect.bisect_left(xs, x)", "Position of the first item >= x in a sorted list"),
    ".bisect_right": ("bisect.bisect_right(xs, x)", "Position of the first item > x in a sorted list"),
    ".next": ("node.next", "A linked-list node's pointer to the next node"),
    ".val": ("node.val", "The value stored in a node"),
    ".left": ("node.left", "Left child in a binary tree"),
    ".right": ("node.right", "Right child in a binary tree"),
    # ---- NumPy
    ".array": ("np.array([1, 2, 3])", "Create an array. R: `c(1, 2, 3)`"),
    ".zeros": ("np.zeros(n) / np.zeros((n, k))", "Array of zeros"),
    ".ones": ("np.ones(n)", "Array of ones"),
    ".arange": ("np.arange(n)", "0 to n-1. R: `0:(n-1)`"),
    ".mean": ("x.mean() / np.mean(x)", "Mean"),
    ".sum": ("x.sum()", "Sum; summing a boolean array counts the Trues"),
    ".std": ("x.std(ddof=1)", "Standard deviation; without `ddof=1` it divides by n"),
    ".var": ("x.var(ddof=1)", "Variance"),
    "ddof=": ("ddof=1", "Divide by n-1 (sample SD / variance, same as R's `sd()`)"),
    "axis=": ("X.mean(axis=0)", "axis=0 works down columns (one value per column); axis=1 across rows. R: `colMeans` / `rowMeans`"),
    ".median": ("np.median(x)", "Median"),
    ".percentile": ("np.percentile(x, [2.5, 97.5])", "Percentiles (argument on a 0-100 scale). R: `quantile()`"),
    ".round": ("x.round(3)", "Round to 3 decimals"),
    ".where": ("np.where(cond, a, b)", "a where the condition holds, otherwise b. R: `ifelse()`"),
    ".sqrt": ("np.sqrt(x)", "Square root"),
    ".exp": ("np.exp(x)", "e to the power x"),
    ".log": ("np.log(x)", "Natural log"),
    ".abs": ("np.abs(x)", "Element-wise absolute value"),
    ".argmax": ("x.argmax()", "Index of the maximum (from 0). R: `which.max()`"),
    ".argmin": ("x.argmin(axis=1)", "Index of the minimum"),
    ".argsort": ("np.argsort(x)", "Original indices in sorted order. R: `order()`"),
    ".cumsum": ("x.cumsum()", "Cumulative sum"),
    ".concatenate": ("np.concatenate([a, b])", "Join into one array. R: `c(a, b)`"),
    ".column_stack": ("np.column_stack([a, b])", "Stack as columns of a matrix. R: `cbind()`"),
    ".bincount": ("np.bincount(labels)", "Count how often 0, 1, 2, ... occur"),
    ".T": ("X.T", "Transpose. R: `t(X)`"),
    ".shape": ("X.shape", "Shape (rows, columns). R: `dim()`"),
    ".linalg": ("np.linalg.solve(A, b)", "Linear algebra module"),
    ".solve": ("np.linalg.solve(A, b)", "Solve Ax = b. R: `solve(A, b)`"),
    ".random": ("rng = np.random.default_rng(42) / rng.random(n)", "Random numbers; `rng.random(n)` is uniform on [0, 1). R: `runif()`"),
    ".default_rng": ("rng = np.random.default_rng(42)", "Create a seeded random generator. R: `set.seed(42)`"),
    ".integers": ("rng.integers(1, 7, size=n)", "Random integers (right end excluded). R: `sample(1:6, n, replace = TRUE)`"),
    ".normal": ("rng.normal(mean, sd, size=n)", "Normal random numbers. R: `rnorm()`"),
    ".exponential": ("rng.exponential(scale, size=n)", "Exponential random numbers. R: `rexp()` (scale is 1/rate)"),
    ".choice": ("rng.choice(x, size=n, replace=True)", "Sample from x. R: `sample()`"),
    "replace=": ("replace=True", "Sample with replacement (for the bootstrap)"),
    "size=": ("size=n", "How many (can also be a shape (rows, cols))"),
    ".permutation": ("rng.permutation(x)", "Random shuffle. R: `sample(x)`"),
    ".tolist": ("s.tolist()", "Convert to a plain list"),
    ".to_numpy": ("df[cols].to_numpy()", "Convert to a NumPy array. R: `as.matrix()`"),
    ".astype": ("s.astype(int)", "Change type; True/False become 1/0. R: `as.integer()`"),
    # ---- pandas
    ".groupby": ('df.groupby("g")["x"].sum()', "Group, then summarize. dplyr: `group_by(g) %>% summarise(sum(x))`"),
    ".agg": ('.agg(new_name=("col", "func"))', "Several named summaries at once, e.g. `total=(\"amount\", \"sum\")`. dplyr: `summarise(total = sum(amount))`"),
    ".reset_index": (".reset_index()", "Turn the group keys from row labels back into columns (common after groupby)"),
    ".rename": ('.rename(columns={"old": "new"})', "Rename columns. Mind the direction: {old: new}"),
    ".merge": ('a.merge(b, on="key", how="left")', "Join on a key. dplyr: `left_join(a, b, by = \"key\")`"),
    "how=": ('how="left"', "Which rows to keep: inner / left / right / outer"),
    "on=": ('on="user_id"', "The column to match on"),
    ".fillna": (".fillna(0)", "Replace missing values with 0. R: `replace_na(x, 0)`"),
    ".dropna": ('.dropna(subset=["col"])', "Drop rows with missing values in these columns. R: `drop_na(col)`"),
    ".isna": (".isna()", "Is it missing. R: `is.na()`"),
    ".drop_duplicates": ('.drop_duplicates(subset=["g"], keep="first")', "Remove duplicates; after sorting it gives 'one row per group'. dplyr: `distinct()`"),
    "subset=": ('subset=["col"]', "Only look at these columns"),
    "keep=": ('keep="first"', "Keep the first duplicate (\"last\" keeps the last one)"),
    ".sort_values": ('.sort_values("x", ascending=False)', "Sort. dplyr: `arrange(desc(x))`"),
    "ascending=": ("ascending=False", "False = largest first; pass a list for several columns"),
    ".head": (".head(n)", "First n rows; after groupby, `.head(1)` is the first row of each group"),
    ".isin": ('s.isin(["a", "b"])', "Is the value in a set of values. R: `%in%`; prefix `~` for 'not in'"),
    ".unique": ("s.unique()", "Distinct values. R: `unique()`"),
    ".nunique": ("s.nunique()", "Number of distinct values. dplyr: `n_distinct()`"),
    ".value_counts": ("s.value_counts()", "How often each value occurs. R: `table()`"),
    ".transform": ('df.groupby("g")["x"].transform("sum")', "Give every row its group's summary, keeping the row count. dplyr: `group_by %>% mutate`"),
    ".rank": ('.rank(method="dense", ascending=False)', "Rank"),
    ".shift": ('.groupby("g")["x"].shift(1)', "The previous row's value. dplyr: `lag()`"),
    ".iloc": ("s.iloc[k] / df.iloc[k]", "The k-th item / row by position (from 0)"),
    ".loc": ('df.loc[cond, "col"]', "Select by condition and column name"),
    ".str": ("s.str.strip() / s.str.upper()", "Element-wise string operations on a column"),
    ".dt": ('s.dt.strftime("%Y-%m") / (d2 - d1).dt.days', "Element-wise date operations on a column"),
    ".to_datetime": ('pd.to_datetime(s, errors="coerce")', "Parse text as dates. R: `as.Date()` / `ymd()`"),
    ".to_numeric": ('pd.to_numeric(s, errors="coerce")', "Convert to numbers. R: `as.numeric()`"),
    "errors=": ('errors="coerce"', "Values that cannot be converted become missing instead of raising"),
    ".strftime": ('.dt.strftime("%Y-%m")', "Format dates as strings, e.g. 2026-01"),
    ".days": ("(d2 - d1).dt.days", "Number of days between two dates"),
    ".pivot_table": ('df.pivot_table(index=, columns=, values=, aggfunc="sum", fill_value=0)', "Long to wide with aggregation. tidyr: `pivot_wider()`"),
    ".melt": ('df.melt(id_vars="id")', "Wide to long. tidyr: `pivot_longer()`"),
    ".concat": ("pd.concat([a, b])", "Stack vertically. R: `bind_rows()`"),
    ".apply": ("s.apply(func)", "Call a function on each element (prefer vectorized column operations)"),
    ".map": ("s.map({old: new})", "Replace values using a lookup table"),
    ".cut": ("pd.cut(s, bins=[...], labels=[...])", "Bin values at cut points. R: `cut()`"),
    ".size": ('df.groupby("g").size()', "Number of rows in each group"),
    # ---- scipy / statsmodels / sklearn
    ".norm": ("stats.norm.ppf(0.975) / stats.norm.sf(z)", "Normal distribution. R: `qnorm()` / `pnorm()`"),
    ".t": ("stats.t.ppf(0.975, df=n-1)", "t distribution. R: `qt(0.975, n - 1)`"),
    ".binom": ("stats.binom.pmf(k, n, p)", "Binomial distribution. R: `dbinom()`; `.cdf` is `pbinom()`"),
    ".ppf": (".ppf(prob)", "Critical value (quantile) for a probability. The q-functions in R"),
    ".sf": (".sf(x)", "Upper-tail probability = 1 - cdf. R: `pnorm(x, lower.tail = FALSE)`"),
    ".cdf": (".cdf(x)", "Lower-tail probability. The p-functions in R"),
    ".pmf": (".pmf(k)", "Probability of a single value. The d-functions in R"),
    "df=": ("df=n-1", "Degrees of freedom"),
    ".ttest_ind": ("stats.ttest_ind(a, b, equal_var=False)", "Two-sample t-test. R: `t.test(a, b)`"),
    "equal_var=": ("equal_var=False", "Welch t-test (no equal-variance assumption; R's default)"),
    ".pvalue": ("res.pvalue", "The p-value of a test result"),
    ".chisquare": ("stats.chisquare(observed, expected)", "Chi-square goodness-of-fit test. R: `chisq.test(x, p = )`"),
    ".ols": ('smf.ols("y ~ x1 + x2", data=df).fit()', "Linear regression. R: `lm(y ~ x1 + x2, data = df)`"),
    ".fit": (".fit()", "Fit the model"),
    ".params": ("res.params", "Coefficients. R: `coef()`"),
    ".pvalues": ("res.pvalues", "p-value of each coefficient"),
    ".bse": ("res.bse", "Standard error of each coefficient"),
    ".conf_int": ("res.conf_int()", "Confidence intervals. R: `confint()`"),
    ".rsquared": ("res.rsquared", "R²"),
    "cov_type=": ('.fit(cov_type="HC3")', "Robust (heteroskedasticity-consistent) standard errors. R: `sandwich::vcovHC`"),
    "LogisticRegression(": ("LogisticRegression(max_iter=1000)", "Logistic regression model (sklearn)"),
    ".predict_proba": ("model.predict_proba(X)[:, 1]", "Predicted probability of class 1 (column 1)"),
    ".predict": ("model.predict(X)", "Predicted class / value"),
    "roc_auc_score(": ("roc_auc_score(y_true, proba)", "ROC-AUC; argument order is (truth, probability)"),
    "average_precision_score(": ("average_precision_score(y_true, proba)", "PR-AUC"),
    "precision_score(": ("precision_score(y_true, pred)", "Precision: of those predicted 1, how many really are 1"),
    "recall_score(": ("recall_score(y_true, pred)", "Recall: of the true 1s, how many were found"),
    "train_test_split(": ("train_test_split(X, y, test_size=0.25, stratify=y, random_state=0)", "Split into training and test sets"),
    "test_size=": ("test_size=0.25", "25% goes to the test set"),
    "stratify=": ("stratify=y", "Keep the positive rate the same in both parts"),
    "random_state=": ("random_state=0", "Random seed, for reproducible results"),
    "cross_val_score(": ('cross_val_score(model, X, y, cv=5, scoring="roc_auc")', "k-fold cross-validation; returns one score per fold"),
    "cv=": ("cv=5", "Number of folds"),
    "scoring=": ('scoring="roc_auc"', "The metric to score with"),
    "GridSearchCV(": ('GridSearchCV(pipe, param_grid={...}, cv=5, scoring="roc_auc")', "Grid search over hyperparameters"),
    "param_grid=": ('param_grid={"model__C": [0.1, 1, 10]}', "Parameters to try; inside a Pipeline write step_name__param"),
    ".best_params_": ("search.best_params_", "The best parameter combination"),
    ".best_score_": ("search.best_score_", "Cross-validated score of the best parameters"),
    ".best_estimator_": ("search.best_estimator_", "The model refit on all training data with the best parameters"),
    "make_pipeline(": ("make_pipeline(StandardScaler(), LogisticRegression())", "Chain preprocessing and the model to prevent leakage"),
    "max_iter=": ("max_iter=1000", "Maximum number of iterations (raise it if it does not converge)"),
}

SQL = {
    "WHERE": ("WHERE cond", "Filter rows (before grouping)"),
    "GROUP": ("GROUP BY col", "Group; every non-aggregated column in SELECT must be listed here"),
    "HAVING": ("HAVING COUNT(*) > 1", "Filter after grouping (aggregates allowed)"),
    "ORDER": ("ORDER BY col DESC", "Sort; DESC is largest first"),
    "LIMIT": ("LIMIT 3", "Only the first 3 rows"),
    "DISTINCT": ("COUNT(DISTINCT user_id)", "Remove duplicates / count distinct values"),
    "COUNT": ("COUNT(*) / COUNT(col)", "Number of rows / number of non-NULL values"),
    "SUM": ("SUM(col)", "Sum"),
    "AVG": ("AVG(col)", "Average; `AVG(cond)` gives a proportion directly (true counts as 1)"),
    "MIN": ("MIN(col)", "Minimum (works on dates too)"),
    "MAX": ("MAX(col)", "Maximum"),
    "CASE": ("CASE WHEN cond THEN a ELSE b END", "Conditional value. R: `case_when()`"),
    "COALESCE": ("COALESCE(x, 0)", "Use 0 when x is NULL. R: `coalesce()`"),
    "JOIN": ("a JOIN b ON a.k = b.k", "Inner join"),
    "LEFT": ("a LEFT JOIN b ON a.k = b.k", "Left join: keeps every left row; unmatched columns are NULL"),
    "IS": ("x IS NULL / IS NOT NULL", "Test for missing (`= NULL` does not work)"),
    "IN": ("x IN ('a', 'b') / x IN (SELECT ...)", "Is the value in a set of values"),
    "BETWEEN": ("x BETWEEN a AND b", "Both ends included"),
    "WITH": ("WITH t AS (SELECT ...) SELECT ... FROM t", "CTE: name an intermediate result and build step by step"),
    "OVER": ("func() OVER (PARTITION BY g ORDER BY x)", "Window function: keeps every row and adds a within-group calculation"),
    "PARTITION": ("PARTITION BY g", "Window groups by g (like groupby, without collapsing rows)"),
    "ROW_NUMBER": ("ROW_NUMBER() OVER (...)", "Number rows 1, 2, 3, ... within the group (ties get different numbers)"),
    "RANK": ("RANK() OVER (...)", "Ties share a rank, then numbers are skipped"),
    "DENSE_RANK": ("DENSE_RANK() OVER (...)", "Ties share a rank, no numbers skipped"),
    "LAG": ("LAG(x) OVER (PARTITION BY g ORDER BY d)", "The previous row's value"),
    "LEAD": ("LEAD(x) OVER (...)", "The next row's value"),
    "STRFTIME": ("STRFTIME('%Y-%m', d)", "Format a date as year-month in SQLite"),
    "DATE": ("DATE(d, '+1 day')", "Date arithmetic in SQLite"),
    "JULIANDAY": ("JULIANDAY(d2) - JULIANDAY(d1)", "Days between two dates in SQLite"),
    "ROUND": ("ROUND(x, 2)", "Round to 2 decimals"),
    "UNION": ("SELECT ... UNION ALL SELECT ...", "Stack two results vertically"),
    "EXISTS": ("WHERE EXISTS (SELECT 1 ...)", "True if the subquery returns any row"),
}

_SYNTAX = {ast.Lambda: "lambda", ast.JoinedStr: "f-string", ast.ListComp: "comprehension",
           ast.DictComp: "comprehension", ast.SetComp: "comprehension", ast.GeneratorExp: "comprehension",
           ast.Try: "try", ast.While: "while", ast.IfExp: "x if c else y"}


def _py_keys(code):
    """Tool keys an answer uses, in the order they appear."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    own = {n.name + "(" for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    found = []
    for n in ast.walk(tree):
        key = None
        if isinstance(n, ast.Attribute):
            key = "." + n.attr
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            key = n.func.id + "("
        elif isinstance(n, ast.keyword) and n.arg:
            key = n.arg + "="
        elif type(n) in _SYNTAX:
            key = _SYNTAX[type(n)]
        elif isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Slice) and n.slice.step is not None:
            key = "[::step]"
        if key and key in PY and key not in own:
            # ast.walk is breadth-first; sort by where the thing ends so a chain reads left to right.
            pos = (getattr(n, "end_lineno", 0) or 0, getattr(n, "end_col_offset", 0) or 0)
            found.append((pos, key))
    seen, out = set(), []
    for _, k in sorted(found):
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def _sql_keys(q):
    q = re.sub(r"'[^']*'", "", q)
    out = []
    for w in re.findall(r"[A-Za-z_]+", q):
        w = w.upper()
        if w in SQL and w not in out:
            out.append(w)
    return out


def answer_tools(code, lang="python"):
    """[(usage, note, key)] for the tools an answer uses."""
    if lang == "sql":
        return [(*SQL[k], k) for k in _sql_keys(code)]
    return [(*PY[k], k) for k in _py_keys(code)]


# ---------------------------------------------------------------- where each tool is first taught
_DETAILS = re.compile(r"<details>.*?</details>", re.S)


def _key_pattern(key, lang):
    if lang == "sql":
        return re.compile(r"(?<![A-Za-z_])" + key + r"(?![A-Za-z_])")
    if key.startswith("."):
        return re.compile(r"\." + re.escape(key[1:]) + r"(?![A-Za-z0-9_])")
    if key.endswith("("):
        return re.compile(r"(?<![A-Za-z0-9_.])" + re.escape(key[:-1]) + r"\(")
    if key.endswith("="):
        return re.compile(r"(?<![A-Za-z0-9_])" + re.escape(key[:-1]) + r"\s*=")
    return {"lambda": re.compile(r"\blambda\b"), "f-string": re.compile(r"\bf\"|\bf'"),
            "comprehension": re.compile(r"\[[^\]\n]* for \w|comprehension"), "try": re.compile(r"\btry\b"),
            "while": re.compile(r"\bwhile\b"), "x if c else y": re.compile(r"\bif\b[^\n:]*\belse\b"),
            "[::step]": re.compile(r"::")}.get(key, re.compile(re.escape(key)))


def first_taught(manifest, notebook_dir):
    """{('python'|'sql', key): lesson id} — the first lesson whose runnable example shows the tool
    (failing that, the first one that mentions it in the explanation). Answers and hints (inside
    <details>) and the exercises themselves don't count. SQL keywords only count in SQL lessons."""
    lessons = []
    for m in manifest:
        try:
            cells = json.loads((Path(notebook_dir) / m["file"]).read_text(encoding="utf-8"))["cells"]
        except Exception:
            continue
        is_sql = any(c.get("metadata", {}).get("lang") == "sql" for c in cells)
        code = {"python": [], "sql": []}
        prose = []
        for c in cells:
            src = c.get("source", "")
            src = "".join(src) if isinstance(src, list) else src
            meta = c.get("metadata", {})
            if c.get("cell_type") == "markdown":
                md = _DETAILS.sub("", src)
                prose += re.findall(r"```.*?```", md, re.S) + re.findall(r"`[^`\n]+`", md)
            elif not (meta.get("check") or meta.get("solution")):
                code["sql" if meta.get("lang") == "sql" else "python"].append(src)
        lessons.append((m["id"], is_sql, {k: "\n".join(v) for k, v in code.items()}, "\n".join(prose)))
    out = {}
    for lang, table in (("python", PY), ("sql", SQL)):
        for key in table:
            pat = _key_pattern(key, lang)
            pool = [x for x in lessons if lang == "python" or x[1]]
            hit = next((lid for lid, _, code, _ in pool if pat.search(code[lang])), None) or \
                next((lid for lid, _, _, prose in pool if pat.search(prose)), None)
            if hit:
                out[(lang, key)] = hit
    return out


# ---------------------------------------------------------------- fill-in version of an answer
BLANK = "____"


def _blank_literals(code):
    """Replace string and number literals with ____, keeping the layout (good for pandas chains)."""
    lines = code.splitlines(keepends=True)
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(code).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return None
    spans = [(t.start, t.end) for t in toks if t.type in (tokenize.STRING, tokenize.NUMBER)]
    if len(spans) < 2:
        return None
    for (sr, sc), (er, ec) in reversed(spans):
        if sr != er:          # a multi-line string: leave it
            continue
        ln = lines[sr - 1]
        lines[sr - 1] = ln[:sc] + BLANK + ln[ec:]
    return "".join(lines)


def _seg(code, node):
    return ast.get_source_segment(code, node) or ""


def _structure(code):
    """Keep the control flow (def / for / while / if / return) and blank out the expressions."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    out = []

    def val(node):
        # Keep a library call's name as a hint (`np.sqrt(____)`); everything else becomes ____.
        if isinstance(node, ast.Call) and re.fullmatch(r"[A-Za-z_][\w.]*", _seg(code, node.func)) and \
                "." in _seg(code, node.func):
            return f"{_seg(code, node.func)}({BLANK})"
        return BLANK

    def stmts(body, ind):
        for s in body:
            emit(s, ind)

    def emit(s, ind):
        p = " " * ind
        if isinstance(s, (ast.FunctionDef, ast.ClassDef)):
            head = _seg(code, s).splitlines()[0]
            out.append(p + head.strip())
            if isinstance(s, ast.ClassDef):
                stmts(s.body, ind + 4)
            else:
                stmts(s.body, ind + 4)
        elif isinstance(s, ast.For):
            out.append(f"{p}for {_seg(code, s.target)} in {BLANK}:")
            stmts(s.body, ind + 4)
        elif isinstance(s, ast.While):
            out.append(f"{p}while {BLANK}:")
            stmts(s.body, ind + 4)
        elif isinstance(s, ast.If):
            out.append(f"{p}if {BLANK}:")
            stmts(s.body, ind + 4)
            orelse = s.orelse
            while len(orelse) == 1 and isinstance(orelse[0], ast.If):
                out.append(f"{p}elif {BLANK}:")
                stmts(orelse[0].body, ind + 4)
                orelse = orelse[0].orelse
            if orelse:
                out.append(f"{p}else:")
                stmts(orelse, ind + 4)
        elif isinstance(s, ast.Try):
            out.append(f"{p}try:")
            stmts(s.body, ind + 4)
            for h in s.handlers:
                out.append(p + "except" + (f" {_seg(code, h.type)}" if h.type is not None else "") + ":")
                stmts(h.body, ind + 4)
        elif isinstance(s, ast.Return):
            out.append(f"{p}return" + (f" {val(s.value)}" if s.value is not None else ""))
        elif isinstance(s, ast.Assign):
            out.append(f"{p}{' = '.join(_seg(code, t) for t in s.targets)} = {val(s.value)}")
        elif isinstance(s, ast.AugAssign):
            op = {ast.Add: "+=", ast.Sub: "-=", ast.Mult: "*=", ast.Div: "/="}.get(type(s.op), "+=")
            out.append(f"{p}{_seg(code, s.target)} {op} {val(s.value)}")
        elif isinstance(s, ast.Expr) and isinstance(s.value, ast.Call):
            out.append(f"{p}{_seg(code, s.value.func)}({BLANK})")
        elif isinstance(s, ast.Expr) and isinstance(s.value, (ast.Name, ast.Constant)):
            return            # a bare `out` that only displays the result
        elif isinstance(s, (ast.Import, ast.ImportFrom, ast.Pass, ast.Break, ast.Continue, ast.Global, ast.Nonlocal)):
            out.append(p + _seg(code, s).strip())
        else:
            out.append(f"{p}{BLANK}")

    stmts(tree.body, 0)
    return "\n".join(out) + "\n"


_SQL_KEEP = set("""SELECT FROM WHERE GROUP BY ORDER HAVING JOIN LEFT RIGHT INNER OUTER FULL ON AS AND OR NOT IN IS NULL
DISTINCT COUNT SUM AVG MIN MAX CASE WHEN THEN ELSE END WITH OVER PARTITION ROW_NUMBER RANK DENSE_RANK LAG LEAD
LIMIT OFFSET UNION ALL BETWEEN LIKE COALESCE CAST ROUND EXISTS DESC ASC ROWS PRECEDING FOLLOWING CURRENT ROW
UNBOUNDED STRFTIME DATE JULIANDAY SUBSTR IFNULL NULLIF CROSS USING ABS LENGTH UPPER LOWER""".split())


def _sql_skeleton(q):
    """Keep the SQL keywords and layout; blank out column / table names, aliases and values."""
    def sub(m):
        w = m.group(0)
        return w if w.upper() in _SQL_KEEP else BLANK
    q = re.sub(r"'[^']*'", BLANK, q)
    q = re.sub(r"\b\d+(\.\d+)?\b", BLANK, q)
    q = re.sub(r"[A-Za-z_][A-Za-z_0-9]*(\.[A-Za-z_][A-Za-z_0-9]*)?", sub, q)
    q = re.sub(rf"{BLANK}(\s*\.\s*{BLANK})+", BLANK, q)
    return q


def skeleton(code, lang="python"):
    """A fill-in version of the answer, or None if there's nothing sensible to blank out."""
    code = code.strip("\n") + "\n"
    if lang == "sql":
        return _sql_skeleton(code)
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    has_flow = any(isinstance(n, (ast.FunctionDef, ast.For, ast.While)) for n in ast.walk(tree))
    out = _structure(code) if has_flow else _blank_literals(code)
    if out is None or out.strip() == code.strip():
        return None
    return out
