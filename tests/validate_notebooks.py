"""Run every lesson the way the app does and report anything that breaks.

For each notebook, in order:
  * Python code cells run in one shared namespace (exercises run their reference answer);
    exercises with a hidden `check` are graded against that answer.
  * SQL exercises run their reference solution against the practice database.
  * Read-only drills (```python block followed by a **Result** ```text block in markdown)
    are executed and their printed output is compared with the text shown.

Usage:  python tests/validate_notebooks.py [--root OTHER_COPY] [notebook-name-substring ...]
Exit code is non-zero when anything fails.
"""
from __future__ import annotations

import ast
import contextlib
import io
import json
import os
import re
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
warnings.filterwarnings("ignore")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import check_helpers  # noqa: E402
import practice_data  # noqa: E402

DETAILS_RE = re.compile(r"<details>\s*<summary>(.*?)</summary>(.*?)</details>", re.S)
DRILL_RE = re.compile(r"```python\n(.*?)```\s*\n\*\*[^*\n]+\*\*\s*\n+```text\n(.*?)```", re.S)
ANSWER_WORDS = ("answer",)


def src(cell):
    s = cell.get("source", "")
    return "".join(s) if isinstance(s, list) else str(s)


def run(code, ns):
    """Execute like the app: last bare expression is evaluated and echoed (repr)."""
    out = io.StringIO()
    tree = ast.parse(code)
    body, last = tree.body, None
    if body and isinstance(body[-1], ast.Expr):
        last = ast.Expression(body[-1].value)
        body = body[:-1]
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        if body:
            exec(compile(ast.Module(body=body, type_ignores=[]), "<cell>", "exec"), ns)
        val = eval(compile(last, "<cell>", "eval"), ns) if last else None
    plt.close("all")
    printed = out.getvalue()
    shown = None
    if val is not None:
        shown = repr(val) if not hasattr(val, "to_string") else str(val)
    return printed, shown


def following_folds(cells, i):
    out = []
    for c in cells[i + 1:]:
        s = src(c).lstrip()
        if c.get("cell_type") != "markdown" or not s.startswith("<details>"):
            break
        out.append(s)
    return out


def answer_of(cells, i):
    for f in following_folds(cells, i):
        m = re.search(r"```python\n(.*?)```", f, re.S)
        if m and any(w in f.split("</summary>")[0].lower() for w in ANSWER_WORDS):
            return m.group(1)
    return None


NUM_RE = re.compile(r"-?\d+(?:\.\d+)?(?:e[-+]?\d+)?")


def same_output(got, shown_text):
    """Shown output matches printed text, the echoed value, or both, up to the shown precision."""
    printed, value = got
    if value is not None:
        value = re.sub(r"np\.(?:float|int)\d+\((.*?)\)", r"\1", value)
    want = norm(shown_text)
    candidates = [printed + (value or ""), printed + "\n" + (value or ""), printed, value or ""]
    for c in candidates:
        c = norm(c)
        if c == want:
            return True
        a, b = NUM_RE.split(c), NUM_RE.split(want)
        if a == b:
            na, nb = NUM_RE.findall(c), NUM_RE.findall(want)
            ok = True
            for x, y in zip(na, nb):
                dec = len(y.split(".")[1]) if "." in y and "e" not in y else 0
                if abs(float(x) - float(y)) > 0.51 * 10 ** (-dec) + 1e-12:
                    ok = False
                    break
            if ok:
                return True
    return False


def norm(t):
    return "\n".join(l.rstrip() for l in t.strip().splitlines())


def validate(path: Path):
    cells = json.loads(path.read_text(encoding="utf-8"))["cells"]
    ns = {"__name__": "__main__"}
    problems, n_checks, n_drills, n_ungraded = [], 0, 0, 0
    for i, c in enumerate(cells):
        meta = c.get("metadata", {})
        s = src(c)
        if c["cell_type"] == "markdown":
            visible = DETAILS_RE.sub("", s)
            drills = {m.start(1): m for m in DRILL_RE.finditer(visible)}
            # Setup / example blocks with no shown output (e.g. "already run at the top
            # of every problem: import numpy as np") run silently so later drills can use them.
            for b in re.finditer(r"```python\n(.*?)```", visible, re.S):
                m = drills.get(b.start(1))
                if m is None:
                    try:
                        run(b.group(1), ns)
                    except Exception:  # noqa: BLE001  pseudocode or deliberate error demos
                        pass
                    continue
                n_drills += 1
                try:
                    got = run(m.group(1), ns)
                except Exception as e:  # noqa: BLE001
                    problems.append(f"cell {i}: drill raised {type(e).__name__}: {e}")
                    continue
                if not same_output(got, m.group(2)):
                    shown_got = got[0] + (got[1] or "")
                    problems.append(f"cell {i}: drill output differs\n    shown: {norm(m.group(2))[:200]!r}\n    got:   {norm(shown_got)[:200]!r}")
            continue
        if c["cell_type"] != "code":
            continue
        exercise = bool(meta.get("check") or meta.get("solution"))
        if meta.get("lang") == "sql":
            if meta.get("solution"):
                n_checks += 1
                try:
                    practice_data.run_sql(meta["solution"])
                except Exception as e:  # noqa: BLE001
                    problems.append(f"cell {i}: SQL solution failed: {e}")
            continue
        code = s
        if exercise:
            ans = answer_of(cells, i)
            if ans is None and meta.get("check"):
                # Timed mock tests (04j, 14b, 14c) deliberately have no answer right
                # below each problem, so there is nothing to grade automatically.
                n_ungraded += 1
                continue
            code = ans or s
        try:
            run(code, ns)
        except Exception as e:  # noqa: BLE001
            if type(e).__name__ != meta.get("expect_error"):  # e.g. a typo demo
                problems.append(f"cell {i}: code raised {type(e).__name__}: {e}")
            continue
        if meta.get("check"):
            n_checks += 1
            cns = dict(ns)
            cns.update(check_helpers.HELPERS)
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    exec(compile(meta["check"], "<check>", "exec"), cns)
            except Exception as e:  # noqa: BLE001
                problems.append(f"cell {i}: check failed: {type(e).__name__}: {e}")
    return problems, n_checks, n_drills, n_ungraded


def main(argv):
    nb_dir = ROOT / "notebooks"
    if argv[:1] == ["--root"]:
        nb_dir, argv = Path(argv[1]) / "notebooks", argv[2:]
    files = sorted(nb_dir.glob("*.ipynb"))
    if argv:
        files = [f for f in files if any(a in f.name for a in argv)]
    bad = 0
    for f in files:
        problems, nc, nd, nu = validate(f)
        status = "OK " if not problems else "FAIL"
        extra = f", {nu} mock-test problems without answers" if nu else ""
        print(f"{status} {f.name}  ({nc} checks, {nd} drills{extra})")
        for p in problems:
            print("    " + p)
        bad += bool(problems)
    print(f"\n{len(files) - bad}/{len(files)} notebooks clean")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
