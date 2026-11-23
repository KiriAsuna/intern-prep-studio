"""Lenient comparison helpers used by the auto-checker (and by the lesson builder's self-test)."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _to_frame(x) -> pd.DataFrame:
    if isinstance(x, pd.Series):
        x = x.reset_index() if not _plain_index(x.index) else x.to_frame()
    elif isinstance(x, pd.DataFrame):
        if not _plain_index(x.index):
            x = x.reset_index()
    else:
        x = pd.DataFrame(x)
    return x


def _plain_index(idx) -> bool:
    # A named index comes from groupby/value_counts and carries data; an unnamed one is just row labels.
    return all(n is None for n in idx.names)


def _norm(v):
    if v is None or v is pd.NaT:
        return None
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, (int, np.integer)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return None if math.isnan(v) else float(v)
    if isinstance(v, pd.Timestamp):
        return v.strftime("%Y-%m-%d") if v == v.normalize() else v.isoformat()
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return str(v)


def _eq(a, b, tol):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        return abs(a - b) <= tol * max(1.0, abs(b))
    return a == b


def _key(row):
    return tuple("" if v is None else (f"{v:.6f}" if isinstance(v, float) else str(v)) for v in row)


def _show(row):
    return "(" + ", ".join("NULL" if v is None else (f"{v:g}" if isinstance(v, float) else str(v)) for v in row) + ")"


def same_frame(got, exp, ordered=False, tol=1e-6):
    """Compare two table-like results. Returns (ok, message)."""
    try:
        got, exp = _to_frame(got), _to_frame(exp)
    except Exception:
        return False, "The result is not a table."
    if got.shape[1] != exp.shape[1]:
        return False, (f"Wrong number of columns: your result has {got.shape[1]}, expected {exp.shape[1]}"
                       f" ({', '.join(map(str, exp.columns))}).")
    gcols, ecols = [str(c).lower() for c in got.columns], [str(c).lower() for c in exp.columns]
    if sorted(gcols) == sorted(ecols) and len(set(gcols)) == len(gcols):
        got = got[[got.columns[gcols.index(c)] for c in ecols]]
    if len(got) != len(exp):
        return False, f"Wrong number of rows: your result has {len(got)}, expected {len(exp)}."
    g = [tuple(_norm(v) for v in r) for r in got.itertuples(index=False, name=None)]
    e = [tuple(_norm(v) for v in r) for r in exp.itertuples(index=False, name=None)]
    gs, es = sorted(g, key=_key), sorted(e, key=_key)
    for a, b in zip(gs, es):
        if not all(_eq(x, y, tol) for x, y in zip(a, b)):
            return False, f"Wrong values: your result has the row {_show(a)} where {_show(b)} was expected. Also check the column order against the problem."
    if ordered:
        for i, (a, b) in enumerate(zip(g, e)):
            if not all(_eq(x, y, tol) for x, y in zip(a, b)):
                return False, f"The values are right but the order is not: row {i + 1} should be {_show(b)}."
    return True, ""


def expect_frame(got, exp, ordered=False, tol=1e-6):
    ok, msg = same_frame(got, exp, ordered=ordered, tol=tol)
    assert ok, msg


def expect_close(got, exp, tol=1e-6, name="result"):
    try:
        g = float(got)
    except Exception:
        raise AssertionError(f"{name} should be a number, but it is {got!r}.")
    assert abs(g - exp) <= tol, f"{name} is {g:.6g}; expected about {exp:.6g}."


def expect_array(got, exp, tol=1e-6, name="result"):
    g, e = np.asarray(got, dtype=float), np.asarray(exp, dtype=float)
    assert g.shape == e.shape, f"{name} has shape {g.shape}; expected {e.shape}."
    assert np.allclose(g, e, atol=tol, rtol=tol, equal_nan=True), f"{name} has the wrong values. Yours: {np.round(g, 4).tolist()}, expected: {np.round(e, 4).tolist()}."


def _listify(x):
    if isinstance(x, (list, tuple)):
        return [_listify(v) for v in x]
    if isinstance(x, np.generic):
        return x.item()
    if isinstance(x, np.ndarray):
        return x.tolist()
    return x


def expect_call(fn, args, expected, norm=None, tol=None):
    """Call fn(*args) on a copy of the inputs and compare with the expected return value."""
    import copy
    name = getattr(fn, "__name__", "function")
    shown = f"{name}({', '.join(repr(a) for a in args)})"
    try:
        got = fn(*copy.deepcopy(args))
    except TimeoutError:
        raise
    except RecursionError:
        raise AssertionError(f"{shown}: the recursion never stops. Check the base case (when it should return directly).")
    except Exception as e:
        raise AssertionError(f"{shown} raised an error: {type(e).__name__}: {e}")
    if got is None and expected is not None:
        raise AssertionError(f"{shown} returned None; expected {expected!r}. Did you forget to return?")
    g, e = _listify(got), _listify(expected)
    if norm is not None:
        try:
            g, e = norm(g), norm(e)
        except Exception:
            raise AssertionError(f"{shown} returned {got!r}; expected {expected!r}.")
    if tol is not None:
        try:
            ok = abs(g - e) <= tol
        except Exception:
            ok = False
    else:
        ok = g == e
    assert ok, f"{shown} returned {got!r}; expected {expected!r}."


def expect_calls(fn, cases, norm=None, tol=None):
    for args, expected in cases:
        expect_call(fn, args, expected, norm=norm, tol=tol)


HELPERS = {"same_frame": same_frame, "expect_frame": expect_frame,
           "expect_close": expect_close, "expect_array": expect_array,
           "expect_call": expect_call, "expect_calls": expect_calls}
