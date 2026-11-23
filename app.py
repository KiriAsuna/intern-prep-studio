from __future__ import annotations

import ast
import copy
import io
import json
import os
import random
import re
import shutil
import sqlite3
import sys
import time
import traceback
from datetime import date, timedelta
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

import warnings

# plt.show() has nothing to show in this app; figures are captured and displayed after the cell runs.
warnings.filterwarnings("ignore", message=".*non-interactive.*")

import pandas as pd
import streamlit as st

import autoshutdown
import check_helpers
import practice_data
import toolbox


ROOT = Path(__file__).resolve().parent
NOTEBOOK_DIR = ROOT / "notebooks"
ICON_FILE = ROOT / "assets" / "icon.png"
# INTERN_PREP_USER_DIR lets a test run use a throwaway folder instead of the real saved work.
USER_DIR = Path(os.environ.get("INTERN_PREP_USER_DIR") or ROOT / "user_data")
USER_DIR.mkdir(exist_ok=True)
_marker = os.environ.get("INTERN_PREP_MARKER")
autoshutdown.start(Path(_marker) if _marker else None)
PROGRESS_FILE = USER_DIR / "progress.json"
NOTES_FILE = USER_DIR / "notes.json"
ANSWERS_FILE = USER_DIR / "answers.json"
REVIEW_FILE = USER_DIR / "review.json"     # spaced-repetition schedule for redoing exercises
BACKUP_DIR = USER_DIR / "backups"

# Newer Streamlit replaces use_container_width with width="stretch"; support both.
_ST_VERSION = tuple(int(x) for x in re.findall(r"\d+", st.__version__)[:2])
STRETCH = {"width": "stretch"} if _ST_VERSION >= (1, 50) else {"use_container_width": True}

st.set_page_config(
    page_title="Intern Prep Studio",
    page_icon=str(ICON_FILE) if ICON_FILE.exists() else "◼",   # also the window's taskbar icon
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
/* Light colours by default; the dark set applies when the system (and so Streamlit) is in dark mode. */
:root {
  --bg: #f6f8fc;
  --glow1: rgba(90,120,240,.08);
  --glow2: rgba(130,110,240,.06);
  --sidebar: #eef2fa;
  --panel-a: #ffffff;
  --panel-b: #f7f9fd;
  --expander: rgba(255,255,255,.85);
  --line: #d9e0ee;
  --line2: #c9d3e6;
  --muted: #5d6b85;
  --accent: #4c6fe8;
  --kicker: #4c6fe8;
  --hero-a: #e9eefc;
  --hero-b: #f4f1ff;
  --hero-sub: #46546e;
  --section: #66748f;
  --badge-text: #44526c;
  --code-bg: #f1f4fa;
  --block-bg: #ebeff7;
  --block-line: #cbd5e8;
  --inline-code-bg: #e6ebf5;
  --indent-guide: rgba(70,90,140,.42);
  --cp-title: #1c2640;
  --cp-detail: #4a5874;
  --cp-time: #4c6fe8;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0b1020;
    --glow1: rgba(124,156,255,.11);
    --glow2: rgba(155,140,255,.08);
    --sidebar: rgba(13,19,35,.96);
    --panel-a: rgba(24,34,56,.98);
    --panel-b: rgba(17,25,43,.98);
    --expander: rgba(18,26,44,.72);
    --line: #27334d;
    --line2: #33415f;
    --muted: #9aa9c6;
    --accent: #7c9cff;
    --kicker: #9fb3ff;
    --hero-a: rgba(32,44,75,.95);
    --hero-b: rgba(20,29,49,.95);
    --hero-sub: #b4c0d8;
    --section: #91a0bd;
    --badge-text: #c7d2ea;
    --code-bg: #090d18;
    --block-bg: #151b2b;
    --block-line: #2c3854;
    --inline-code-bg: #1d2436;
    --indent-guide: rgba(190,205,255,.30);
    --cp-title: #f3f6ff;
    --cp-detail: #b7c3dc;
    --cp-time: #a8b9ff;
  }
}

.stApp {
  background:
    radial-gradient(circle at 15% 10%, var(--glow1), transparent 26%),
    radial-gradient(circle at 85% 0%, var(--glow2), transparent 24%),
    var(--bg);
}
[data-testid="stSidebar"] {
  background: var(--sidebar);
  border-right: 1px solid var(--line);
}
.block-container {padding-top: 2rem; padding-bottom: 5rem; max-width: 1280px;}
h1,h2,h3,h4 {letter-spacing: -.02em;}
h1 {font-size: 2.15rem !important;}
h2 {margin-top: 1.4rem !important;}
p, li {line-height: 1.72;}
small, .muted {color: var(--muted);}
div[data-testid="stMetric"] {
  background: linear-gradient(180deg, var(--panel-a), var(--panel-b));
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 15px 17px;
}
div[data-testid="stMetricLabel"] {color: var(--muted);}
div[data-testid="stMetricValue"] {font-size: 1.8rem;}
div[data-testid="stExpander"] {
  border: 1px solid var(--line);
  background: var(--expander);
  border-radius: 14px;
}
.stButton > button {
  border-radius: 12px;
  border: 1px solid var(--line2);
  min-height: 42px;
}
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #6f8fff, #8e80ff);
  color: white;
  border: 0;
}
.stTextArea textarea, .stTextInput input {
  border-radius: 12px !important;
}
/* Streamlit 1.65 wraps the box in stTextAreaRootElement, older versions in a baseweb textarea div.
   Leave the focused box alone so it keeps the accent outline. */
.stTextArea [data-testid="stTextAreaRootElement"]:not(:focus-within),
.stTextArea [data-baseweb="textarea"]:not(:focus-within) {
  border-color: var(--block-line) !important;
}
/* Code boxes (keys start with "code_") use a monospace font so indentation lines up; notes stay in the text font. */
[class*="st-key-code_"] textarea {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace !important;
  font-size: 0.9rem !important;
  line-height: 1.5 !important;
}
/* Indent guides (drawn by EDITOR_KEYS_JS): a copy of the text in transparent ink sits behind the
   code box, and the leading spaces of each line carry a thin line at every 4-column stop. */
.ipk-guides {
  position: absolute;
  box-sizing: border-box;
  overflow: hidden;
  pointer-events: none;
  color: transparent;
  white-space: pre-wrap;
  overflow-wrap: break-word;
  margin: 0;
  z-index: 0;
}
.ipk-guides .ipk-line { min-height: var(--ipk-lh); }
.ipk-guides .ipk-ind {
  display: inline-block;
  vertical-align: top;
  height: var(--ipk-lh);
  background-image: repeating-linear-gradient(to right, var(--indent-guide) 0 1px, transparent 1px 4ch);
}
.course-card {
  background: linear-gradient(145deg, var(--panel-a), var(--panel-b));
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 18px 20px;
  margin: 8px 0 12px 0;
  min-height: 148px;
}
.course-id {
  color: var(--accent);
  font-weight: 700;
  letter-spacing: .08em;
  font-size: .78rem;
  text-transform: uppercase;
}
.course-title {font-size: 1.15rem; font-weight: 700; margin-top: 8px;}
.course-sub {color: var(--muted); margin-top: 4px;}
.badge {
  display: inline-block;
  padding: 4px 9px;
  border: 1px solid var(--line2);
  border-radius: 999px;
  color: var(--badge-text);
  font-size: .76rem;
  margin-top: 12px;
}
.hero {
  padding: 28px 30px;
  background: linear-gradient(135deg, var(--hero-a), var(--hero-b));
  border: 1px solid var(--line);
  border-radius: 24px;
  margin-bottom: 20px;
}
.hero-kicker {
  color: var(--kicker);
  font-weight: 700;
  letter-spacing: .09em;
  text-transform: uppercase;
  font-size: .78rem;
}
.hero-title {
  font-size: 2.35rem;
  font-weight: 800;
  letter-spacing: -.04em;
  margin-top: 8px;
}
.hero-sub {
  color: var(--hero-sub);
  max-width: 760px;
  font-size: 1.02rem;
  margin-top: 9px;
  line-height: 1.65;
}
.section-label {
  color: var(--section);
  text-transform: uppercase;
  letter-spacing: .08em;
  font-size: .74rem;
  font-weight: 700;
  margin-bottom: 8px;
}
.hr {height:1px;background:var(--line);margin:18px 0 22px;}
/* Code blocks and inline code inside lesson text: Streamlit's default fill is almost the page colour
   in light mode, so give them their own fill and a border. */
[data-testid="stMarkdownPre"] pre {
  background: var(--block-bg) !important;
  border: 1px solid var(--block-line) !important;
  border-radius: 10px !important;
}
.stMarkdown p code, .stMarkdown li code, .stMarkdown td code, .stMarkdown blockquote code {
  background: var(--inline-code-bg) !important;
}
.code-output {
  background: var(--code-bg);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 12px 14px;
  white-space: pre-wrap;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
div[data-testid="stProgress"] > div > div > div > div {
  background: linear-gradient(90deg, #7391ff, #a084ff);
}
.checkpoint {
  background: linear-gradient(135deg, rgba(124,156,255,.16), rgba(155,140,255,.10));
  border: 1px solid rgba(124,156,255,.48);
  border-left: 5px solid #7c9cff;
  border-radius: 16px;
  padding: 15px 18px;
  margin: 18px 0 22px;
}
.checkpoint-time {
  color: var(--cp-time);
  font-size: .78rem;
  font-weight: 800;
  letter-spacing: .10em;
  text-transform: uppercase;
}
.checkpoint-title {
  color: var(--cp-title);
  font-size: 1.04rem;
  font-weight: 750;
  margin-top: 4px;
}
.checkpoint-detail {
  color: var(--cp-detail);
  margin-top: 5px;
  line-height: 1.55;
}
.timeline-row {
  border-left: 2px solid var(--line2);
  padding: 2px 0 18px 18px;
  margin-left: 8px;
}
.timeline-hour {color:var(--kicker);font-weight:800;}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Older Streamlit (e.g. 1.50) has no per-mode accent colour in config.toml, so it shows its
# default red there. Recolour the few widgets that use it; newer versions take the colour from config.
def _supports_mode_accent():
    try:
        from streamlit import config as _stc
        return "theme.light.primaryColor" in _stc._config_options
    except Exception:
        return True

if not _supports_mode_accent():
    st.markdown("""
<style>
[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) > div:first-child {
  background-color: var(--accent) !important;
}
[data-testid="stCheckbox"] label[data-baseweb="checkbox"]:has(input:checked) > span:first-child {
  background-color: var(--accent) !important;
  border-color: var(--accent) !important;
}
[data-testid="stSlider"] [data-baseweb="slider"] > div > div {
  filter: hue-rotate(225deg);
}
.stTextArea [data-baseweb="textarea"]:focus-within {
  border-color: var(--accent) !important;
}
</style>
""", unsafe_allow_html=True)

# Editor behaviour for every text box, close to VS Code with Python:
#   Tab / Shift+Tab indent and dedent (4 spaces; Tab in mid-line pads to the next 4-column stop);
#   Enter keeps the indentation, one level deeper after ":" and one level shallower after
#   return / pass / break / continue / raise; typing the ":" of else / elif / except / finally
#   moves that line back one level; Backspace inside the leading spaces deletes back to the previous stop.
# Code boxes (keys "code_...") also get indent guides. Installed once on the page; execCommand keeps
# the browser's undo history working.
EDITOR_KEYS_JS = r"""
<script>
(function () {
  const w = window.parent, doc = w.document;
  if (w.__internPrepKeys) return;
  w.__internPrepKeys = true;
  const INDENT = '    ';
  let busy = false;   // our own edits fire input events too; ignore them
  function replace(ta, start, end, text, selStart, selEnd) {
    busy = true;
    ta.focus();
    ta.setSelectionRange(start, end);
    let ok = false;
    try { ok = doc.execCommand('insertText', false, text); } catch (e) {}
    if (!ok) {
      const setter = Object.getOwnPropertyDescriptor(w.HTMLTextAreaElement.prototype, 'value').set;
      setter.call(ta, ta.value.slice(0, start) + text + ta.value.slice(end));
      ta.dispatchEvent(new w.Event('input', {bubbles: true}));
    }
    ta.setSelectionRange(selStart, selEnd);
    busy = false;
  }
  function leading(line) { return line.match(/^ */)[0].length; }
  doc.addEventListener('keydown', function (e) {
    const ta = e.target;
    if (!ta || ta.tagName !== 'TEXTAREA' || e.ctrlKey || e.metaKey || e.altKey || e.isComposing) return;
    const v = ta.value, s = ta.selectionStart, en = ta.selectionEnd;
    if (e.key === 'Tab') {
      e.preventDefault();
      e.stopPropagation();
      const multi = v.slice(s, en).includes('\n');
      if (!e.shiftKey && !multi) {
        const col = s - (v.lastIndexOf('\n', s - 1) + 1), n = 4 - col % 4;
        replace(ta, s, en, ' '.repeat(n), s + n, s + n);
        return;
      }
      const lineStart = v.lastIndexOf('\n', s - 1) + 1;
      let lineEnd = v.indexOf('\n', en);
      if (lineEnd < 0) lineEnd = v.length;
      if (multi && v[en - 1] === '\n') lineEnd = en - 1;
      let firstDelta = 0, total = 0;
      const out = v.slice(lineStart, lineEnd).split('\n').map(function (ln, i) {
        if (!e.shiftKey) { if (i === 0) firstDelta = 4; total += 4; return INDENT + ln; }
        const m = ln.match(/^ {1,4}|^\t/), k = m ? m[0].length : 0;
        if (i === 0) firstDelta = -k;
        total -= k;
        return ln.slice(k);
      });
      replace(ta, lineStart, lineEnd, out.join('\n'), Math.max(lineStart, s + firstDelta), Math.max(lineStart, en + total));
    } else if (e.key === 'Enter' && !e.shiftKey) {
      const lineStart = v.lastIndexOf('\n', s - 1) + 1, before = v.slice(lineStart, s);
      let ind = before.match(/^[ \t]*/)[0];
      if (/:\s*(#.*)?$/.test(before)) ind += INDENT;
      else if (/^\s*(return|pass|break|continue|raise)\b/.test(before)) ind = ind.slice(0, Math.max(0, ind.length - 4));
      if (!ind && !/^\s/.test(before)) return;
      e.preventDefault();
      replace(ta, s, en, '\n' + ind, s + 1 + ind.length, s + 1 + ind.length);
    } else if (e.key === 'Backspace' && !e.shiftKey && s === en) {
      // Inside the leading spaces of a line, delete back to the previous 4-column stop.
      const lineStart = v.lastIndexOf('\n', s - 1) + 1, before = v.slice(lineStart, s);
      if (!before || !/^ +$/.test(before)) return;
      const k = before.length % 4 || 4;
      if (k < 2) return;
      e.preventDefault();
      replace(ta, s - k, s, '', s - k, s - k);
    }
  }, true);

  // Typing the ":" that completes else / elif / except / finally: if the line still sits at the
  // indentation of the block above it, move it back one level so it lines up with its if / try.
  doc.addEventListener('input', function (e) {
    const ta = e.target;
    if (busy || !ta || ta.tagName !== 'TEXTAREA' || !e.data || e.data.slice(-1) !== ':' || e.isComposing) return;
    const v = ta.value, s = ta.selectionStart;
    if (s !== ta.selectionEnd) return;
    const lineStart = v.lastIndexOf('\n', s - 1) + 1;
    let lineEnd = v.indexOf('\n', s);
    if (lineEnd < 0) lineEnd = v.length;
    const line = v.slice(lineStart, lineEnd);
    if (!/^ {4,}(else|elif\b.*|except\b.*|finally)\s*:\s*$/.test(line)) return;
    let p = lineStart - 1, prev = null;
    while (p > 0) {
      const ps = v.lastIndexOf('\n', p - 1) + 1, cand = v.slice(ps, p);
      if (cand.trim()) { prev = cand; break; }
      p = ps - 1;
    }
    if (prev === null || leading(line) < leading(prev)) return;
    replace(ta, lineStart, lineStart + 4, '', s - 4, s - 4);
  }, true);

  // ---- indent guides for the code boxes ----
  const SEL = '[class*="st-key-code_"] textarea';
  const boxes = new Set();
  function esc(t) { return t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
  function levels(lines) {
    const lv = lines.map(function (ln) { return ln.trim() ? Math.floor(leading(ln) / 4) : -1; });
    // A blank line inside a block keeps the guides of the lines around it.
    for (let i = 0; i < lv.length; i++) {
      if (lv[i] >= 0) continue;
      let a = 0, b = 0;
      for (let j = i - 1; j >= 0; j--) if (lv[j] >= 0) { a = lv[j]; break; }
      for (let j = i + 1; j < lv.length; j++) if (lines[j].trim()) { b = Math.floor(leading(lines[j]) / 4); break; }
      lv[i] = -1 - Math.min(a, b);   // negative marks "blank", value keeps the level
    }
    return lv;
  }
  function draw(box) {
    const ta = box.ta, g = box.g, v = ta.value;
    if (v === box.last) return;
    box.last = v;
    const lines = v.split('\n'), lv = levels(lines);
    g.innerHTML = lines.map(function (ln, i) {
      const blank = lv[i] < 0, L = blank ? -1 - lv[i] : lv[i];
      const ind = L ? '<span class="ipk-ind" style="width:' + (4 * L) + 'ch"></span>' : '';
      const rest = blank ? '' : ln.slice(4 * L);
      return '<div class="ipk-line">' + ind + esc(rest) + '</div>';
    }).join('');
    // Fit the box to the code so the whole block stays in view, as in an editor, but never make it
    // smaller than the height Streamlit gave it.
    if (box.minH == null) box.minH = ta.offsetHeight;
    ta.style.height = box.minH + 'px';
    const need = ta.scrollHeight + ta.offsetHeight - ta.clientHeight;
    if (need > box.minH + 1) ta.style.height = need + 'px';
    g.scrollTop = ta.scrollTop;
  }
  function place(box) {
    const ta = box.ta, g = box.g, cs = w.getComputedStyle(ta);
    g.style.top = (ta.offsetTop + ta.clientTop) + 'px';
    g.style.left = (ta.offsetLeft + ta.clientLeft) + 'px';
    g.style.width = ta.clientWidth + 'px';
    g.style.height = ta.clientHeight + 'px';
    ['paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft', 'fontFamily', 'fontSize',
     'fontWeight', 'lineHeight', 'letterSpacing', 'whiteSpace', 'overflowWrap', 'wordBreak']
      .forEach(function (k) { g.style[k] = cs[k]; });
    g.style.setProperty('--ipk-lh', cs.lineHeight);
    box.last = null;
    draw(box);
  }
  function attach(ta) {
    for (const b of Array.from(boxes)) {
      if (b.ta !== ta) continue;
      if (b.g.isConnected && b.g.parentElement === ta.parentElement) return;
      b.g.remove();          // Streamlit rebuilt the box around the same text area
      boxes.delete(b);
    }
    const host = ta.parentElement;
    if (w.getComputedStyle(host).position === 'static') host.style.position = 'relative';
    const g = doc.createElement('div');
    g.className = 'ipk-guides';
    g.setAttribute('aria-hidden', 'true');
    host.insertBefore(g, ta);
    ta.style.position = 'relative';
    ta.style.zIndex = '1';
    ta.spellcheck = false;                       // no red squiggles under variable names
    ta.setAttribute('autocapitalize', 'off');
    ta.setAttribute('autocorrect', 'off');
    const box = {ta: ta, g: g, last: null};
    boxes.add(box);
    ta.addEventListener('scroll', function () { g.scrollTop = ta.scrollTop; });
    ta.addEventListener('input', function () { draw(box); });
    if (w.ResizeObserver) new w.ResizeObserver(function () { place(box); }).observe(ta);
    place(box);
  }
  function scan() {
    for (const b of Array.from(boxes)) if (!b.ta.isConnected) { b.g.remove(); boxes.delete(b); }
    doc.querySelectorAll(SEL).forEach(attach);
  }
  let pending = false;
  new w.MutationObserver(function () {
    if (pending) return;
    pending = true;
    w.setTimeout(function () { pending = false; scan(); }, 150);
  }).observe(doc.body, {childList: true, subtree: true});
  // Streamlit sets a box's text itself when you press "Reset" (no input event), so check now and then.
  w.setInterval(function () { boxes.forEach(draw); }, 500);
  scan();
})();
</script>
"""

SCROLL_TOP_JS = r"""
<script>
// lesson: %s
(function () {
  const doc = window.parent.document;
  function up() {
    [doc.querySelector('[data-testid="stMain"]'), doc.querySelector('section.main'),
     doc.querySelector('[data-testid="stAppViewContainer"]'), doc.scrollingElement]
      .forEach(function (el) { if (el) el.scrollTop = 0; });
  }
  // The new lesson is drawn in pieces, so keep the view at the top for a moment,
  // but let go as soon as the reader scrolls or types.
  let stop = false;
  ['wheel', 'touchstart', 'keydown', 'mousedown'].forEach(function (ev) {
    doc.addEventListener(ev, function () { stop = true; }, {once: true, capture: true, passive: true});
  });
  up();
  let n = 0;
  const timer = setInterval(function () {
    if (stop || ++n > 25) { clearInterval(timer); return; }
    up();
  }, 100);
})();
</script>
"""

def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def load_user_json(path: Path, default):
    """Load saved work. A damaged file is set aside and the newest backup is used instead of silently starting empty."""
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        BACKUP_DIR.mkdir(exist_ok=True)
        shutil.copy2(path, BACKUP_DIR / f"{path.stem}_damaged_{int(time.time())}{path.suffix}")
        for bak in sorted(BACKUP_DIR.glob(f"{path.stem}_2*{path.suffix}"), reverse=True):
            try:
                return json.loads(bak.read_text(encoding="utf-8"))
            except Exception:
                continue
        return default

def save_json(path: Path, obj):
    # Write to a temp file first so a crash mid-write cannot corrupt the saved file.
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    for attempt in range(20):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            # A sync tool or antivirus may hold the file open for a moment (Windows); wait and retry.
            time.sleep(0.1)
    os.replace(tmp, path)

def backup_user_data(tag: str):
    BACKUP_DIR.mkdir(exist_ok=True)
    for f in (PROGRESS_FILE, NOTES_FILE, ANSWERS_FILE, REVIEW_FILE):
        dst = BACKUP_DIR / f"{f.stem}_{tag}{f.suffix}"
        if f.exists() and not dst.exists():
            shutil.copy2(f, dst)

# One snapshot per day, taken the first time the app runs that day.
backup_user_data(date.today().strftime("%Y%m%d"))

manifest = load_json(ROOT / "course_manifest.json", [])

# Milestones shown at the end of the last lesson of each stage.
END = 10 ** 6
CHECKPOINTS = [
    {"chapter_id": "01h", "cell": END, "title": "Python basics done",
     "detail": "You can write functions, loops and dict / set code, solve Two Sum, and explain why changing b after b = a also changes a."},
    {"chapter_id": "02f", "cell": END, "title": "pandas done",
     "detail": "You can filter, group and aggregate, merge and handle dates, and compute conversion rates, the top row per group, DAU and retention on your own."},
    {"chapter_id": "03f", "cell": END, "title": "SQL done",
     "detail": "You can write GROUP BY / HAVING, LEFT JOIN, CTEs and window functions on the spot, and solve business questions such as retention and consecutive logins."},
    {"chapter_id": "04j", "cell": END, "title": "Algorithms done: ready for the OA coding section",
     "detail": "You have practiced each of the ten common patterns and can pass 3 or more problems in a timed mock. Keep doing 1-2 problems a day from here on."},
    {"chapter_id": "06b", "cell": END, "title": "Probability and inference done",
     "detail": "You can both explain and compute in Python: CIs, p-values, power, the bootstrap and permutation tests."},
    {"chapter_id": "08b", "cell": END, "title": "Regression and classification done",
     "detail": "You can answer OLS-assumption questions layer by layer and hold up under follow-ups, and fit, interpret and evaluate models with statsmodels and scikit-learn."},
    {"chapter_id": "09b", "cell": END, "title": "A/B testing done",
     "detail": "You can design a complete experiment, compute the sample size, analyze the results and write up a conclusion for stakeholders, and you know common pitfalls such as SRM and peeking."},
    {"chapter_id": "11b", "cell": END, "title": "Machine learning done",
     "detail": "You can compare common models, run a leak-free modeling workflow, and code AUC, kNN, k-means and gradient descent from scratch."},
    {"chapter_id": "13", "cell": END, "title": "Case studies and communication done",
     "detail": "You have a go-to framework for metric-drop questions, plus usable 30-second and 2-minute research pitches and a failure story."},
    {"chapter_id": "14c", "cell": END, "title": "All lessons done",
     "detail": "Once you pass all three final reviews, move on to mock interviews, the capstone and daily maintenance practice; no new material."},
]

CHAPTERS = {
    "00": "Start here", "01": "Python basics", "02": "NumPy and pandas", "03": "SQL", "04": "Algorithms and OA",
    "05": "Probability", "06": "Statistical inference", "07": "Linear regression",
    "08": "Logistic regression and regularization", "09": "A/B testing", "10": "Machine learning",
    "11": "Model evaluation and ML from scratch", "12": "DS case studies",
    "13": "Research communication and behavioral", "14": "Final review", "15": "Baseline diagnostic",
}

progress = load_user_json(PROGRESS_FILE, {"completed": [], "ratings": {}, "practice": {}})
notes = load_user_json(NOTES_FILE, {})
answers = load_user_json(ANSWERS_FILE, {})
review = load_user_json(REVIEW_FILE, {})
review.setdefault("cards", {})          # cell key -> {"due", "ivl", "reps", "lapses", "last", "hist"}
review.setdefault("new_per_day", 8)
review.setdefault("introduced", {})     # date -> how many exercises entered review that day

def is_done(mid):
    return mid in progress.get("completed", [])

def set_done(mid, value):
    done = set(progress.get("completed", []))
    if value:
        done.add(mid)
    else:
        done.discard(mid)
    progress["completed"] = sorted(done)
    save_json(PROGRESS_FILE, progress)

def notebook_cells(filename):
    obj = json.loads((NOTEBOOK_DIR / filename).read_text(encoding="utf-8"))
    return obj["cells"]

def source_text(cell):
    src = cell.get("source", "")
    return "".join(src) if isinstance(src, list) else str(src)

def _run_with_deadline(fn, timeout):
    """Run fn(); abort learner code that loops forever."""
    deadline = time.time() + timeout

    def tracer(frame, event, arg):
        if time.time() > deadline:
            raise TimeoutError(f"Stopped after running for more than {timeout} seconds. This is usually an infinite loop: check the while condition, or whether the loop variable gets updated.")
        return tracer if frame.f_code.co_filename == "<exercise>" else None

    sys.settrace(tracer)
    try:
        return fn()
    finally:
        sys.settrace(None)

def _friendly_error(e: BaseException) -> str:
    frames = [f for f in traceback.extract_tb(e.__traceback__) if f.filename == "<exercise>"]
    where = " → ".join(f"line {f.lineno}" + ("" if f.name == "<module>" else f" (in {f.name})") for f in frames)
    msg = "".join(traceback.format_exception_only(type(e), e)).strip()
    return (f"Error at: {where}\n" if where else "") + msg

def _grab_figures():
    plt = sys.modules.get("matplotlib.pyplot")
    images = []
    if plt is not None:
        for num in plt.get_fignums():
            buf = io.BytesIO()
            plt.figure(num).savefig(buf, format="png", dpi=110, bbox_inches="tight")
            images.append(buf.getvalue())
        plt.close("all")
    return images

def execute_python(code: str, namespace: dict, timeout: int = 20):
    stdout = io.StringIO()
    stderr = io.StringIO()
    result_repr = None
    try:
        tree = ast.parse(code, filename="<exercise>", mode="exec")
        body = tree.body
        last_expr = None
        if body and isinstance(body[-1], ast.Expr):
            last_expr = ast.Expression(body[-1].value)
            body = body[:-1]

        def go():
            value = None
            if body:
                exec(compile(ast.Module(body=body, type_ignores=[]), "<exercise>", "exec"), namespace)
            if last_expr is not None:
                value = eval(compile(last_expr, "<exercise>", "eval"), namespace)
            return value

        with redirect_stdout(stdout), redirect_stderr(stderr):
            result_repr = _run_with_deadline(go, timeout)
        return True, stdout.getvalue(), stderr.getvalue(), result_repr
    except Exception as e:
        return False, stdout.getvalue(), _friendly_error(e), None

def run_check(check_code: str, namespace: dict, timeout: int = 20):
    """Run a cell's hidden asserts against a copy of the namespace. Returns (passed, message)."""
    ns = dict(namespace)
    ns.update(check_helpers.HELPERS)
    try:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            _run_with_deadline(lambda: exec(compile(check_code, "<check>", "exec"), ns), timeout)
        return True, ""
    except AssertionError as e:
        return False, str(e) or "The result does not match what was expected."
    except TimeoutError as e:
        return False, str(e)
    except NameError as e:
        m = re.search(r"name '(\w+)' is not defined", str(e))
        name = m.group(1) if m else "?"
        return False, f"`{name}` was not found. Variable and function names must match the problem exactly."
    except Exception as e:
        return False, f"Your code raised an error on the test data: {type(e).__name__}: {e}"

def run_sql_cell(query: str, meta: dict):
    """Run a SQL cell against a fresh copy of the practice database."""
    q = "\n".join(l for l in query.splitlines() if not l.strip().startswith("--")).strip().rstrip(";").strip()
    out = {"ok": True, "out": "", "err": "", "result": None, "verdict": None, "expected": None, "images": []}
    if not q:
        out.update(ok=False, err="No SQL written yet.")
        return out
    try:
        out["result"] = practice_data.run_sql(q)
    except Exception as e:
        cause = getattr(e, "__cause__", None) or e
        msg = str(cause)
        if "one statement at a time" in msg:
            msg = "Only one statement can run at a time: remove the semicolons in between."
        out.update(ok=False, err=f"SQL error: {msg}")
        return out
    if meta.get("solution"):
        expected = practice_data.run_sql(meta["solution"])
        ok, msg = check_helpers.same_frame(out["result"], expected, ordered=bool(meta.get("ordered")))
        out["verdict"] = (ok, msg)
        if not ok:
            out["expected"] = expected
    return out

DETAILS_RE = re.compile(r"<details>\s*<summary>(.*?)</summary>(.*?)</details>", re.S)

def clean_markdown(md: str):
    # Streamlit only renders $...$ / $$...$$ math, so convert LaTeX \[ \] and \( \).
    md = re.sub(r"\\\[(.+?)\\\]", lambda m: "$$" + m.group(1) + "$$", md, flags=re.S)
    md = re.sub(r"\\\((.+?)\\\)", lambda m: "$" + m.group(1).strip() + "$", md, flags=re.S)
    return md

def render_markdown(src: str):
    """Markdown cell; <details> blocks become expanders so code and math inside render properly."""
    pos = 0
    for m in DETAILS_RE.finditer(src):
        before = src[pos:m.start()].strip()
        if before:
            st.markdown(clean_markdown(before), unsafe_allow_html=True)
        label = re.sub(r"<[^>]+>", "", m.group(1)).strip() or "Details"
        with st.expander(label):
            st.markdown(clean_markdown(m.group(2).strip()), unsafe_allow_html=True)
        pos = m.end()
    rest = src[pos:].strip()
    if rest:
        st.markdown(clean_markdown(rest), unsafe_allow_html=True)

def cell_key_of(chapter_id, idx, cell):
    # `cid` is a stable id written by the lesson builder; older lessons fall back to position.
    return cell.get("metadata", {}).get("cid") or f"{chapter_id}_{idx}"

def is_exercise(cell):
    meta = cell.get("metadata", {})
    return bool(meta.get("check") or meta.get("solution"))

@st.cache_data(show_spinner=False)
def _practice_frames():
    return dict(zip(practice_data.TABLES, practice_data.load_tables()))

@st.cache_data(show_spinner=False)
def _capstone_frames():
    return dict(zip(["users", "events"], practice_data.load_capstone()))

def lesson_table_source(cells):
    """Which built-in tables a lesson works with: the capstone pair, the practice database, or none."""
    text = "\n".join(source_text(c) for c in cells if c.get("cell_type") == "code")
    if "load_capstone" in text:
        return _capstone_frames
    if "load_tables" in text or any(c.get("metadata", {}).get("lang") == "sql" for c in cells):
        return _practice_frames
    return None

FRAME_MAKERS = re.compile(r"DataFrame\(|read_csv|load_tables|load_capstone")

def assigned_frame_names(code):
    """Top-level names a cell sets to a freshly built DataFrame (pd.DataFrame(...), load_tables(), ...)."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set()
    names = set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and FRAME_MAKERS.search(ast.get_source_segment(code, node.value) or ""):
            for t in node.targets:
                names |= {n.id for n in ast.walk(t) if isinstance(n, ast.Name)}
    return names

def mentioned(name, text):
    # Non-ASCII letters count as word characters for \b, so only look at ASCII neighbours.
    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])", text) is not None

def render_table_preview(tables, missing):
    """A fold-out view of the tables an exercise uses, so the task can be written without scrolling back."""
    if not tables and not missing:
        return
    names = list(tables) + missing
    with st.expander("📋 Tables used here: " + ", ".join(names) + " (open to see what they look like)"):
        for name, df in tables.items():
            kind = lambda t: "int" if t.startswith("int") else "float" if t.startswith("float") else \
                "date" if t.startswith("datetime") else "bool" if t == "bool" else "text" if t in ("object", "str", "string") else t
            dtypes = ", ".join(f"{c} ({kind(t)})" for c, t in df.dtypes.astype(str).items())
            st.markdown(f"**`{name}`** · {len(df)} rows × {df.shape[1]} columns")
            st.caption("Columns: " + dtypes)
            if len(df) <= 60:
                st.dataframe(df, **STRETCH, hide_index=True, height=min(38 + 35 * len(df), 420))
            else:
                st.dataframe(df.head(10), **STRETCH, hide_index=True)
                st.caption(f"Showing the first 10 of {len(df)} rows.")
        for name in missing:
            st.caption(f"Run the code box above that defines `{name}` first, then it will show here.")

# Words that hint at a table when the task names none. Singular "order" is left out on purpose:
# "in descending order" is too common in task text.
TABLE_HINTS = {"users": ["user", "users", "country", "channel", "signup_date"],
               "orders": ["orders", "order_id", "order_date", "amount", "status", "completed"],
               "events": ["event", "events", "event_type", "event_date"],
               "employees": ["employee", "employees", "manager", "managers", "dept", "salary", "manager_id"]}

def following_folds(cells, idx):
    """The <details> cells (hint, answer) right after an exercise."""
    out = []
    for nxt in cells[idx + 1:]:
        nsrc = source_text(nxt).lstrip()
        if nxt.get("cell_type") != "markdown" or not nsrc.startswith("<details>"):
            break
        out.append(nsrc)
    return out

def exercise_task(md_cells):
    """The exercise's own instructions: markdown above it from its heading on, without earlier answers."""
    above = re.sub(r"<details>.*?</details>", "", "\n".join(md_cells), flags=re.S)
    heads = [m.start() for m in re.finditer(r"^#+ ", above, re.M)]
    return above[heads[-1]:] if heads else above

def exercise_tables(cells, idx, task, namespace, defined, builtin):
    """Tables an exercise uses: named in its task, starter or answer (or guessed from column words)."""
    cell = cells[idx]
    # The answer may use a table the task only describes in words (e.g. "orders"). The
    # `users, orders, ... = load_tables()` setup line names every table, so drop it.
    text = task + "\n" + source_text(cell) + "\n" + str(cell.get("metadata", {}).get("solution") or "")
    text += "\n" + "\n".join(following_folds(cells, idx))
    text = "\n".join(l for l in text.splitlines() if not FRAME_MAKERS.search(l))
    frames = builtin() if builtin else {}
    tables, missing = {}, []
    for name in list(frames) + sorted(defined - set(frames)):
        if not mentioned(name, text):
            continue
        obj = frames.get(name, namespace.get(name))
        if isinstance(obj, pd.DataFrame):
            tables[name] = obj
        elif name not in namespace:
            missing.append(name)
    if not tables and not missing and builtin is _practice_frames:
        tables = {n: frames[n] for n, ws in TABLE_HINTS.items()
                  if n in frames and any(w in text if not w.isascii() else mentioned(w, text) for w in ws)}
    return tables, missing

def exercise_answer(cell, folds):
    """(reference answer, language) of an exercise."""
    meta = cell.get("metadata", {})
    if meta.get("lang") == "sql":
        return meta.get("solution") or "", "sql"
    for f in folds:
        m = re.search(r"```python\n(.*?)```", f, re.S)
        if m and "answer" in f.split("</summary>")[0].lower():
            return m.group(1), "python"
    return "", "python"

@st.cache_data(show_spinner=False)
def _taught_map():
    return toolbox.first_taught(manifest, NOTEBOOK_DIR)

def _put_in_editor(wkey, out_key, text):
    st.session_state[wkey] = text
    st.session_state.pop(out_key, None)

def render_exercise_aids(lesson_id, cell, folds, wkey, out_key):
    """Two steps between a blank editor and the answer: which tools to use, then a fill-in version."""
    ans, lang = exercise_answer(cell, folds)
    if not ans.strip():
        return
    order = {m["id"]: i for i, m in enumerate(manifest)}
    here, taught = order.get(lesson_id, 0), _taught_map()
    tools = toolbox.answer_tools(ans, lang)
    if tools:
        with st.expander(f"🧰 Tools for this problem ({len(tools)} · open if you forget; lists the tools, not the solution)"):
            rows = []
            for usage, desc, key in tools:
                lid = taught.get((lang, key))
                where = ("new in this problem" if lid is None or order.get(lid, 10 ** 6) > here
                         else "covered in this lesson" if lid == lesson_id else f"covered in {lid}")
                rows.append(f"- `{usage}` &nbsp; {desc} &nbsp; <span class='muted'>· {where}</span>")
            st.markdown("\n".join(rows), unsafe_allow_html=True)
    if "____" in source_text(cell):
        return          # already a fill-in exercise
    skel = toolbox.skeleton(ans, lang)
    if skel:
        with st.expander("🪜 Stuck? Switch to the fill-in version (try on your own first)"):
            st.caption("This is the skeleton of the answer: the steps and functions are kept, and column names, values and conditions are blanked out as ____. Fill them in, then run.")
            st.code(skel, language=lang)
            st.button("Put the fill-in version in the code box above", key=f"skel_{wkey}", on_click=_put_in_editor,
                      args=(wkey, out_key, skel))

def reset_cell(widget_key, cell_key, src):
    st.session_state[widget_key] = src
    st.session_state.pop(f"out_{cell_key}", None)
    if cell_key in answers:
        answers.pop(cell_key)
        save_json(ANSWERS_FILE, answers)

def render_code_cell(chapter_id, idx, cell, src, namespace, folds=None, review_key=None):
    """One code box. `review_key` set: a review attempt that starts from the starter code and isn't saved."""
    meta = cell.get("metadata", {})
    lang = meta.get("lang", "python")
    ck = cell_key_of(chapter_id, idx, cell)
    uid = review_key or ck
    exercise = is_exercise(cell)
    passed_before = ck in progress.get("checks", [])
    if review_key:
        label = "Review · write it from scratch; checked when you run it"
    elif exercise:
        label = "Exercise · passed ✅" if passed_before else "Exercise · checked when you run it"
    elif meta.get("role") == "example":
        label = "Example · just click Run"
    else:
        label = "Code"
    if lang == "sql":
        label = "SQL " + label
    st.markdown(f'<div class="section-label">{label}</div>', unsafe_allow_html=True)

    wkey = f"code_{uid}"
    if wkey not in st.session_state:
        st.session_state[wkey] = src if review_key else answers.get(ck, src)
    n_lines = max(src.count("\n"), st.session_state[wkey].count("\n")) + 1
    code = st.text_area("Code", height=max(120, min(520, 80 + 20 * n_lines)), key=wkey, label_visibility="collapsed")
    if not review_key and code != answers.get(ck, src):
        answers[ck] = code
        save_json(ANSWERS_FILE, answers)

    out_key = f"out_{uid}"
    b1, b2, b3 = st.columns([1, 1, 4])
    with b1:
        run = st.button("Run", key=f"run_{uid}", type="primary", **STRETCH)
    with b2:
        if review_key:
            st.button("Start over", key=f"reset_{uid}", on_click=_put_in_editor, args=(wkey, out_key, src), **STRETCH)
        else:
            st.button("Reset", key=f"reset_{uid}", on_click=reset_cell, args=(wkey, ck, src), **STRETCH)
    with b3:
        if review_key:
            st.caption("What you write during review does not overwrite the answer saved in the lesson.")
        elif lang == "sql":
            st.caption("Your work is saved automatically. Available tables: users, orders, events, employees.")
        else:
            st.caption("Your work is saved automatically. Variables defined earlier in the lesson can be used later on.")

    if run:
        if exercise and "____" in code:
            st.session_state[out_key] = {"blank": True}
        elif lang == "sql":
            st.session_state[out_key] = run_sql_cell(code, meta)
        else:
            timeout = int(meta.get("timeout", 20))
            ok, out, err, result = execute_python(code, namespace, timeout)
            images = _grab_figures()
            verdict = run_check(meta["check"], namespace, timeout) if (meta.get("check") and ok) else None
            st.session_state[out_key] = {"ok": ok, "out": out, "err": err, "result": result,
                                         "verdict": verdict, "expected": None, "images": images}
        verdict = st.session_state[out_key].get("verdict")
        if verdict and verdict[0] and not passed_before:
            progress["checks"] = sorted(set(progress.get("checks", [])) | {ck})
            save_json(PROGRESS_FILE, progress)

    # Keep the last output of every cell on screen across reruns.
    last = st.session_state.get(out_key)
    if last and last.get("blank"):
        st.warning("There are still unfilled `____` blanks. Replace each `____` with the right code, then run.")
    elif last:
        if last["out"]:
            st.code(last["out"], language="text")
        result = last["result"]
        if result is not None:
            if isinstance(result, pd.DataFrame):
                st.dataframe(result, **STRETCH, hide_index=(lang == "sql"))
                if lang == "sql":
                    st.caption(f"{len(result)} rows")
            elif isinstance(result, pd.Series):
                st.dataframe(result.to_frame(), **STRETCH)
            else:
                st.write(result)
        for img in last.get("images") or []:
            st.image(img)
        if last["err"]:
            if last["ok"]:
                st.warning(last["err"])
            else:
                st.error(last["err"])
                if lang != "sql":
                    st.caption("Read the last line: it gives the error type and the reason.")
                    if "NameError" in last["err"]:
                        st.caption("If this name is defined in an earlier code box, run the earlier boxes from top to bottom first (exercises need to pass). After a page refresh they need to be run again.")
        verdict = last.get("verdict")
        if verdict:
            if verdict[0]:
                st.success("✅ Passed")
            else:
                st.error(f"❌ Not yet: {verdict[1]}")
                if last.get("expected") is not None:
                    with st.expander("What the correct result looks like (the result only, not the code)"):
                        st.dataframe(last["expected"], **STRETCH, hide_index=True)

    if exercise and folds is not None:
        render_exercise_aids(chapter_id, cell, folds, wkey, out_key)

def page_header(kicker, title, subtitle):
    st.markdown(
        f"""
        <div class="hero">
          <div class="hero-kicker">{kicker}</div>
          <div class="hero-title">{title}</div>
          <div class="hero-sub">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_checkpoint(cp, compact=False):
    detail = "" if compact else f'<div class="checkpoint-detail">{cp["detail"]}</div>'
    st.markdown(
        f"""<div class="checkpoint">
        <div class="checkpoint-time">CHECKPOINT · By now you should be able to</div>
        <div class="checkpoint-title">{cp['title']}</div>
        {detail}
        </div>""",
        unsafe_allow_html=True,
    )

def chapter_checkpoints(chapter_id):
    return [cp for cp in CHECKPOINTS if cp["chapter_id"] == chapter_id]

def parse_questions():
    text = (ROOT / "interview_question_bank.md").read_text(encoding="utf-8")
    items = []
    section = "General"
    for line in text.splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
        m = re.match(r"^\s*(\d+)\.\s+(.*)", line)
        if m:
            items.append({"section": section, "q": m.group(2).strip(), "n": int(m.group(1))})
    return items

def dashboard():
    page_header(
        "INTERVIEW PREP SYSTEM",
        "Intern Prep Studio",
        "Each session, do just the lesson under \"Continue\" below. Finish them all and you will meet the bar for typical DS / ML / statistics intern interviews and OAs."
    )

    total = len(manifest)
    done = len(progress.get("completed", []))
    pct = done / total if total else 0

    a,b,c,d = st.columns(4)
    a.metric("Lessons done", f"{done}/{total}")
    b.metric("Overall progress", f"{pct:.0%}")
    minutes_total = sum(x["minutes"] for x in manifest)
    minutes_done = sum(x["minutes"] for x in manifest if is_done(x["id"]))
    c.metric("Study time completed", f"{minutes_done//60}h {minutes_done%60}m")
    c.caption(f"About {minutes_total/60:.1f} hours planned in total")
    ratings = [v for v in progress.get("ratings", {}).values() if isinstance(v, (int,float))]
    d.metric("Average self-rating", f"{sum(ratings)/len(ratings):.1f}/5" if ratings else "—")

    st.progress(pct)
    st.caption("On the first pass, aim to understand, type it out and get it running; closed-book work and follow-up questions are for the second pass.")

    st.markdown("### Continue")
    next_mod = next((m for m in manifest if not is_done(m["id"])), manifest[-1] if manifest else None)
    if next_mod:
        st.markdown(
            f"""<div class="course-card">
            <div class="course-id">NEXT · {next_mod['id']}</div>
            <div class="course-title">{next_mod['title']}</div>
            <div class="course-sub">{next_mod['subtitle']}</div>
            <span class="badge">{next_mod['group']}</span>
            <span class="badge">about {next_mod['minutes']} min</span>
            </div>""",
            unsafe_allow_html=True
        )
        if st.button("Open this lesson", type="primary", **STRETCH):
            st.session_state["page"] = "Lessons"
            st.session_state["chapter_id"] = next_mod["id"]
            st.rerun()

    due, fresh = review_queue()
    st.markdown("### Today's review")
    if due or fresh:
        st.markdown(f"**{len(due)}** due and **{len(fresh)}** new exercises to write again from scratch. Review first, then move on to the new lesson.")
        if st.button("Start review", **STRETCH):
            st.session_state["page"] = "Review"
            st.rerun()
    else:
        st.caption("Nothing to review today." if review["cards"] or progress.get("completed")
                   else "After you finish a lesson, its exercises come back every few days for you to write again from scratch.")

    with st.expander("Milestones: what you should be able to do at each stage"):
      st.caption("For pacing, follow the \"10-Week Plan\" page. This only lists the bar for each stage.")
      left_cp, right_cp = st.columns(2)
      for i, cp in enumerate(CHECKPOINTS):
        with (left_cp if i < 5 else right_cp):
            st.markdown(
                f"""<div class="timeline-row">
                <div class="timeline-hour">After {cp['chapter_id']}</div>
                <b>{cp['title']}</b><br>
                <span class="muted">{cp['detail']}</span>
                </div>""",
                unsafe_allow_html=True,
            )

    st.markdown("### Roadmap")
    st.caption("16 chapters. Open one to see its lessons; ✅ means done.")
    checks_done = set(progress.get("checks", []))
    for cid, cname in CHAPTERS.items():
        lessons = [m for m in manifest if m["id"][:2] == cid]
        if not lessons:
            continue
        n_done = sum(is_done(m["id"]) for m in lessons)
        hours = sum(m["minutes"] for m in lessons) / 60
        mark = "✅" if n_done == len(lessons) else ("🟡" if n_done else "⬜")
        with st.expander(f"{mark} {cid} · {cname} ({n_done}/{len(lessons)} lessons, about {hours:.1f} h)"):
            for m in lessons:
                st.markdown(f"{'✅' if is_done(m['id']) else '⬜'} **{m['id']}** {m['title']} · "
                            f"<span class='muted'>{m['subtitle']} · {m['minutes']} min</span>", unsafe_allow_html=True)

def course_page():
    page_header("COURSE", "Lessons", "Work through them in order: explanation → example → modify → fill in → write your own. Exercises are checked automatically and your work is saved automatically.")

    default_id = st.session_state.get("chapter_id", manifest[0]["id"] if manifest else "00")
    ids = [m["id"] for m in manifest]
    default_idx = ids.index(default_id) if default_id in ids else 0

    selected = st.selectbox(
        "Lesson",
        manifest,
        index=default_idx,
        format_func=lambda m: f"{m['id']}  {m['title']}  ·  {m['subtitle']}",
    )
    st.session_state["chapter_id"] = selected["id"]
    # Opening a different lesson starts at its top, not wherever the previous page was scrolled to.
    if st.session_state.get("_shown_lesson") != selected["id"]:
        st.session_state["_shown_lesson"] = selected["id"]
        st.session_state["_scroll_top"] = f"{selected['id']}-{time.time()}"

    left, right = st.columns([3,1])
    with left:
        st.markdown(f"## {selected['id']} · {selected['title']}")
        st.caption(selected["subtitle"])
    with right:
        st.metric("Estimated time", f"{selected['minutes']} min")

    done_value = st.checkbox(
        "Lesson done",
        value=is_done(selected["id"]),
        key=f"done_{selected['id']}"
    )
    if done_value != is_done(selected["id"]):
        set_done(selected["id"], done_value)
        st.rerun()

    rating = st.slider(
        "Self-rated mastery",
        1, 5,
        int(progress.get("ratings", {}).get(selected["id"], 3)),
        key=f"rating_{selected['id']}"
    )
    if progress.get("ratings", {}).get(selected["id"]) != rating:
        progress.setdefault("ratings", {})[selected["id"]] = rating
        save_json(PROGRESS_FILE, progress)

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

    ns_key = f"namespace_{selected['id']}"
    if ns_key not in st.session_state:
        st.session_state[ns_key] = {"__name__": "__main__"}
    namespace = st.session_state[ns_key]

    cells = notebook_cells(selected["file"])
    cps_here = chapter_checkpoints(selected["id"])
    builtin = lesson_table_source(cells)
    task_text = []          # markdown since the previous code cell: the exercise's instructions
    defined = set()         # names assigned by earlier cells that build DataFrames
    for idx, cell in enumerate(cells):
        for cp in cps_here:
            if cp["cell"] == idx:
                render_checkpoint(cp)
        ctype = cell.get("cell_type")
        src = source_text(cell)
        if ctype == "markdown":
            render_markdown(src)
            task_text.append(src)
        elif ctype == "code":
            folds = None
            if is_exercise(cell):
                task = exercise_task(task_text)
                render_table_preview(*exercise_tables(cells, idx, task, namespace, defined, builtin))
                folds = following_folds(cells, idx)
            else:
                defined |= assigned_frame_names(src)
            render_code_cell(selected["id"], idx, cell, src, namespace, folds=folds)
            task_text = []

    ex_keys = [cell_key_of(selected["id"], i, c) for i, c in enumerate(cells) if is_exercise(c)]
    if ex_keys:
        n_passed = sum(1 for k in ex_keys if k in progress.get("checks", []))
        st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
        st.caption(f"Exercises passed in this lesson: {n_passed}/{len(ex_keys)}")
        st.progress(n_passed / len(ex_keys))

    pos = ids.index(selected["id"])
    if pos + 1 < len(manifest):
        nxt = manifest[pos + 1]
        if st.button(f"Finish this lesson and go to the next: {nxt['id']} {nxt['title']}", type="primary", **STRETCH):
            set_done(selected["id"], True)
            st.session_state.pop(f"done_{selected['id']}", None)
            st.session_state["chapter_id"] = nxt["id"]
            st.rerun()

    for cp in cps_here:
        if cp["cell"] >= len(cells):
            render_checkpoint(cp)

    st.markdown("### Notes for this lesson")
    nkey = f"note_{selected['id']}"
    if nkey not in st.session_state:
        st.session_state[nkey] = notes.get(selected["id"], "")
    note = st.text_area(
        "Things you tend to forget, mistakes, and explanations in your own words",
        height=180,
        key=nkey,
        label_visibility="collapsed"
    )
    if note != notes.get(selected["id"], ""):
        notes[selected["id"]] = note
        save_json(NOTES_FILE, notes)
    st.caption("Notes are saved automatically to user_data/notes.json (click outside the box to save).")

# ---------------------------------------------------------------- review (spaced repetition)
# Every exercise of a finished lesson (or one already passed) comes back to be written again from a
# blank box: after 1 day if it went badly, then at growing gaps (≈4 → 10 → 25 → 60 days) while it goes well.

@st.cache_data(show_spinner=False)
def exercise_index():
    """All exercises in course order: key, lesson, cell position, title, task text."""
    items = []
    for m in manifest:
        cells = notebook_cells(m["file"])
        md_since = []
        for idx, c in enumerate(cells):
            if c.get("cell_type") == "markdown":
                md_since.append(source_text(c))
                continue
            if is_exercise(c):
                task = exercise_task(md_since)
                title = re.sub(r"^#+\s*(✏️\s*)?", "", task.strip().splitlines()[0]) if task.strip() else "Exercise"
                items.append({"ck": cell_key_of(m["id"], idx, c), "lid": m["id"], "idx": idx,
                              "title": title, "task": task})
            md_since = []
    return items

def today_iso():
    return date.today().isoformat()

def next_interval(card, grade):
    ivl, reps = card.get("ivl", 0), card.get("reps", 0)
    if grade == "again":
        return 1
    if grade == "hard":
        return 2 if reps == 0 else max(2, round(ivl * 1.5))
    return 4 if reps == 0 else max(ivl + 2, round(ivl * 2.5))

def grade_card(ck, grade, rkey):
    t = today_iso()
    is_new = ck not in review["cards"]
    card = review["cards"].get(ck, {"ivl": 0, "reps": 0, "lapses": 0, "hist": []})
    ivl = next_interval(card, grade)
    card.update(ivl=ivl, due=(date.today() + timedelta(days=ivl)).isoformat(), last=t,
                reps=card.get("reps", 0) + (grade != "again"), lapses=card.get("lapses", 0) + (grade == "again"))
    card["hist"] = (card.get("hist", []) + [[t, grade]])[-30:]
    review["cards"][ck] = card
    if is_new:
        week_ago = (date.today() - timedelta(days=7)).isoformat()
        review["introduced"] = {d: n for d, n in review["introduced"].items() if d >= week_ago}
        review["introduced"][t] = review["introduced"].get(t, 0) + 1
    save_json(REVIEW_FILE, review)
    # Forget this attempt, so the next time the exercise comes up it starts from a blank box again.
    for k in [k for k in st.session_state if isinstance(k, str) and rkey in k]:
        st.session_state.pop(k, None)
    st.session_state.pop(f"rv_nonce_{ck}", None)

def review_queue():
    """(due, new): exercises to redo today. New ones come in course order, a few per day."""
    t = today_iso()
    cards = review["cards"]
    eligible = set(progress.get("completed", []))
    checks = set(progress.get("checks", []))
    items = exercise_index()
    due = sorted((it for it in items if it["ck"] in cards and cards[it["ck"]].get("due", t) <= t),
                 key=lambda it: cards[it["ck"]].get("due", t))
    room = max(0, int(review.get("new_per_day", 8)) - review["introduced"].get(t, 0))
    fresh = [it for it in items if it["ck"] not in cards and (it["lid"] in eligible or it["ck"] in checks)][:room]
    return due, fresh

def review_namespace(lesson, cells, upto):
    """Variables the exercise expects: run the lesson's examples and reference answers above it."""
    key = f"rvns_{lesson['id']}_{upto}"
    if key not in st.session_state:
        ns = {"__name__": "__main__"}
        with st.spinner("Preparing the variables this exercise needs (running the earlier examples in the lesson)..."):
            for i, c in enumerate(cells[:upto]):
                meta = c.get("metadata", {})
                if c.get("cell_type") != "code" or meta.get("lang") == "sql":
                    continue
                code = exercise_answer(c, following_folds(cells, i))[0] if is_exercise(c) else source_text(c)
                if code.strip():
                    execute_python(code, ns, int(meta.get("timeout", 20)))
            _grab_figures()
        st.session_state[key] = ns
    return st.session_state[key]

def _fresh_copy(ns):
    out = {}
    for k, v in ns.items():
        if isinstance(v, (pd.DataFrame, pd.Series, list, dict, set)) or type(v).__name__ == "ndarray":
            try:
                v = v.copy() if hasattr(v, "copy") else copy.copy(v)
            except Exception:
                pass
        out[k] = v
    return out

def render_review_card(item, position=None):
    lesson = next(m for m in manifest if m["id"] == item["lid"])
    cells = notebook_cells(lesson["file"])
    cell = cells[item["idx"]]
    ck = item["ck"]
    card = review["cards"].get(ck)
    nonce = st.session_state.setdefault(f"rv_nonce_{ck}", str(int(time.time() * 1000)))
    rkey = f"rv_{ck}_{nonce}"

    where = f"{position} · " if position else ""
    st.markdown(f"#### {where}{item['lid']} {lesson['title']} · {item['title']}")
    if card:
        st.caption(f"Review #{card.get('reps', 0) + card.get('lapses', 0) + 1} · last time {card.get('last', '—')}"
                   + (f" · missed {card['lapses']} time(s) before" if card.get("lapses") else ""))
    else:
        st.caption("First review: you did this in the lesson; now write it again from a blank box without looking at your old answer.")
    body = item["task"].strip().split("\n", 1)
    if len(body) > 1 and body[1].strip():
        render_markdown(body[1])

    base = review_namespace(lesson, cells, item["idx"])
    ns_key = f"rvrun_{rkey}"
    if ns_key not in st.session_state:
        st.session_state[ns_key] = _fresh_copy(base)
    namespace = st.session_state[ns_key]
    defined = set()
    for c in cells[:item["idx"]]:
        if c.get("cell_type") == "code" and not is_exercise(c):
            defined |= assigned_frame_names(source_text(c))
    render_table_preview(*exercise_tables(cells, item["idx"], item["task"], namespace, defined,
                                          lesson_table_source(cells)))
    folds = following_folds(cells, item["idx"])
    render_code_cell(item["lid"], item["idx"], cell, source_text(cell), namespace, folds=folds, review_key=rkey)
    for f in folds:
        render_markdown(f)

    verdict = (st.session_state.get(f"out_{rkey}") or {}).get("verdict")
    passed = bool(verdict and verdict[0])
    st.markdown("**How did it go?** Pick one to move on to the next exercise.")
    c1, c2, c3 = st.columns(3)
    c = card or {}
    c1.button(f"😵 Couldn't do it / looked at the answer (back in {next_interval(c, 'again')} day)", key=f"g_again_{rkey}",
              on_click=grade_card, args=(ck, "again", rkey), **STRETCH)
    c2.button(f"😐 Got it, but struggled / used the tools or fill-in version ({next_interval(c, 'hard')} days)", key=f"g_hard_{rkey}",
              on_click=grade_card, args=(ck, "hard", rkey), disabled=not passed, **STRETCH)
    c3.button(f"😀 Smooth ({next_interval(c, 'good')} days)", key=f"g_good_{rkey}", type="primary",
              on_click=grade_card, args=(ck, "good", rkey), disabled=not passed, **STRETCH)
    if not passed:
        st.caption("The last two buttons unlock once your code passes.")

def review_page():
    page_header("REVIEW", "Review: write it again every few days",
                "Redo exercises you've done from a blank box, without the answer. If it goes smoothly, the next review comes later; if not, it's back tomorrow. Do this first each day, then the new lesson.")
    mode = st.radio("Mode", ["Today's review", "Pick one to redo"], horizontal=True, label_visibility="collapsed")
    if mode == "Today's review":
        due, fresh = review_queue()
        queue = due + fresh
        a, b, c = st.columns(3)
        a.metric("Due today", len(due))
        b.metric("New today", len(fresh))
        c.metric("In review", len(review["cards"]))
        with st.expander("How is review scheduled?"):
            st.markdown(
                "- Exercises from lessons you've finished (and exercises you've already passed) are added a few per day, in course order;\n"
                "- Each one starts from a **blank** box, without the code you wrote in the lesson; the tables, 🧰 tools, 🪜 fill-in version, hints and answer are below, to open as needed;\n"
                "- Grade yourself afterwards: **couldn't do it** → back tomorrow; **struggled** → a slightly longer gap; **smooth** → 4, 10, 25 days... growing each time;\n"
                "- Records are kept in `user_data/review.json`, separate from the answers saved in the lessons.")
            n = st.number_input("Max new exercises per day", 0, 30, int(review.get("new_per_day", 8)))
            if n != review.get("new_per_day"):
                review["new_per_day"] = int(n)
                save_json(REVIEW_FILE, review)
                st.rerun()
        st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
        if not queue:
            st.success("Today's review is done.")
            upcoming = sorted(v.get("due", "") for v in review["cards"].values())
            if upcoming:
                st.caption(f"The next batch is due on {upcoming[0]}. For extra practice, switch to \"Pick one to redo\".")
            elif not progress.get("completed"):
                st.caption("Once you finish a lesson (tick \"Lesson done\"), its exercises enter review.")
            return
        render_review_card(queue[0], f"{len(queue)} left")
    else:
        items = exercise_index()
        lessons = [m for m in manifest if any(it["lid"] == m["id"] for it in items)]
        done = set(progress.get("completed", []))
        default = next((i for i, m in enumerate(lessons) if m["id"] not in done), 0)
        lesson = st.selectbox("Lesson", lessons, index=max(0, default - 1),
                              format_func=lambda m: f"{'✅ ' if m['id'] in done else ''}{m['id']}  {m['title']}")
        mine = [it for it in items if it["lid"] == lesson["id"]]
        cards = review["cards"]
        pick = st.selectbox("Exercise", mine, key=f"rv_pick_{lesson['id']}",
                            format_func=lambda it: it["title"] + (f" (next review {cards[it['ck']]['due']})"
                                                                  if it["ck"] in cards else ""))
        st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
        render_review_card(pick)

def practice_page():
    page_header("PRACTICE", "Interview Questions", "Answer out loud in 90 seconds, then rate yourself. Don't look anything up first.")
    questions = parse_questions()
    sections = ["All"] + sorted(set(x["section"] for x in questions))
    section = st.selectbox("Category", sections)
    pool = questions if section == "All" else [x for x in questions if x["section"] == section]

    if "practice_q" not in st.session_state or st.session_state.get("practice_section") != section:
        st.session_state["practice_q"] = random.choice(pool)
        st.session_state["practice_section"] = section

    q = st.session_state["practice_q"]
    st.markdown(f"### Q{q['n']}. {q['q']}")
    pkey = f"practice_answer_{q['n']}"
    akey = f"practice_{q['n']}"
    if pkey not in st.session_state:
        st.session_state[pkey] = answers.get(akey, "")
    answer = st.text_area("First write down how you would answer (saved automatically)", height=180, key=pkey)
    if answer != answers.get(akey, ""):
        answers[akey] = answer
        save_json(ANSWERS_FILE, answers)
    c1,c2,c3 = st.columns([1,1,3])
    with c1:
        if st.button("Another one", type="primary", **STRETCH):
            st.session_state["practice_q"] = random.choice(pool)
            st.rerun()
    with c2:
        if st.button("Flag for review", **STRETCH):
            flagged = set(progress.setdefault("practice", {}).get("flagged", []))
            flagged.add(q["n"])
            progress["practice"]["flagged"] = sorted(flagged)
            save_json(PROGRESS_FILE, progress)
            st.success("Added to the review list.")
    st.markdown("#### Self-rating")
    rating = st.radio(
        "How well can you answer this now?",
        [1,2,3,4,5],
        horizontal=True,
        captions=["Can't", "Keywords only", "Mostly right", "Clear and complete", "Handles follow-ups"]
    )
    if st.button("Save rating"):
        progress.setdefault("practice", {}).setdefault("ratings", {})[str(q["n"])] = rating
        save_json(PROGRESS_FILE, progress)
        st.success("Saved.")

    flagged = progress.get("practice", {}).get("flagged", [])
    if flagged:
        with st.expander(f"Flagged for review ({len(flagged)})"):
            qmap = {x["n"]: x for x in questions}
            for n in flagged:
                if n in qmap:
                    st.write(f"Q{n}. {qmap[n]['q']}")

def sql_page():
    page_header("SQL LAB", "SQL Lab", "Query the capstone database directly. It is opened read-only, so your practice cannot damage it.")
    db = ROOT / "data" / "capstone.db"
    st.markdown("**Available tables**")
    c1,c2 = st.columns(2)
    c1.code("users", language="text")
    c2.code("events", language="text")

    starter = """SELECT
  acq_channel,
  COUNT(*) AS users,
  AVG(converted) AS conversion_rate
FROM users
GROUP BY acq_channel
ORDER BY conversion_rate DESC;"""
    query = st.text_area("SQL", value=starter, height=240, key="code_sqllab")
    if st.button("Run SQL", type="primary"):
        normalized = query.strip().lower()
        if not (normalized.startswith("select") or normalized.startswith("with")):
            st.error("SQL Lab only allows SELECT / WITH queries.")
        else:
            try:
                con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
                df = pd.read_sql_query(query, con)
                con.close()
                st.dataframe(df, **STRETCH, height=420)
                st.caption(f"{len(df)} rows")
            except Exception as e:
                st.error(str(e))

    with st.expander("Columns of the users table"):
        st.code("user_id, country, age, acq_channel, signup_date, treatment, converted, revenue_30d")
    with st.expander("Columns of the events table"):
        st.code("user_id, event_date, event_type")

def markdown_page(kicker, title, subtitle, filename):
    page_header(kicker, title, subtitle)
    text = (ROOT / filename).read_text(encoding="utf-8")
    st.markdown(text)

def settings_page():
    page_header("SETTINGS", "Data & Settings", "Progress and notes are stored only in the user_data folder inside the app folder.")
    st.markdown("### Export")
    export = {
        "progress": progress,
        "notes": notes,
        "answers": answers,
        "review": review,
    }
    st.download_button(
        "Export study records (JSON)",
        data=json.dumps(export, ensure_ascii=False, indent=2),
        file_name="intern_prep_progress.json",
        mime="application/json",
        **STRETCH,
    )

    st.markdown("### Reset")
    st.warning("This clears completion status, self-ratings, notes and the code you wrote. A backup is saved to user_data/backups first.")
    confirm = st.checkbox("Yes, I want to reset")
    if st.button("Clear all study records", disabled=not confirm):
        backup_user_data("before_reset_" + time.strftime("%Y%m%d_%H%M%S"))
        save_json(PROGRESS_FILE, {"completed": [], "ratings": {}, "practice": {}})
        save_json(NOTES_FILE, {})
        save_json(ANSWERS_FILE, {})
        save_json(REVIEW_FILE, {})
        st.success("Reset done. The previous records were backed up to user_data/backups. Refresh the page to see the change.")

# Sidebar
st.sidebar.markdown("## Intern Prep Studio")
st.sidebar.caption("DS / ML / Statistics Intern")
st.sidebar.markdown("---")

pages = ["Home", "Lessons", "Review", "Interview Questions", "SQL Lab", "Capstone", "Mock Interview",
         "Mastery Checklist", "10-Week Plan", "Settings"]
# A link like ?lesson=03e opens that lesson directly.
_linked = st.query_params.get("lesson")
if _linked and st.session_state.get("_linked_lesson") != _linked and any(m["id"] == _linked for m in manifest):
    st.session_state["_linked_lesson"] = _linked
    st.session_state["page"] = "Lessons"
    st.session_state["chapter_id"] = _linked
current = st.session_state.get("page", "Home")
if current not in pages:
    current = "Home"
page = st.sidebar.radio("Navigation", pages, index=pages.index(current), label_visibility="collapsed")
st.session_state["page"] = page

done = len(progress.get("completed", []))
st.sidebar.markdown("---")
st.sidebar.caption("Overall completion")
st.sidebar.progress(done / len(manifest) if manifest else 0)
st.sidebar.caption(f"{done}/{len(manifest)} modules")
st.sidebar.markdown("---")
st.sidebar.caption("Next lesson")
_next = next((m for m in manifest if not is_done(m["id"])), None)
if _next:
    st.sidebar.markdown(f"**{_next['id']}** · {_next['title']} (about {_next['minutes']} min)")
else:
    st.sidebar.markdown("**All done**")
_due, _fresh = review_queue()
if _due or _fresh:
    st.sidebar.caption(f"Today's review: {len(_due) + len(_fresh)}")

if page == "Home":
    dashboard()
elif page == "Lessons":
    course_page()
elif page == "Review":
    review_page()
elif page == "Interview Questions":
    practice_page()
elif page == "SQL Lab":
    sql_page()
elif page == "Capstone":
    markdown_page("CAPSTONE", "Capstone Project", "From raw data all the way to an experiment, a model and a write-up.", "CAPSTONE.md")
elif page == "Mock Interview":
    markdown_page("MOCK", "Mock Interviews", "Three full interviews, graded with the same rubric.", "mock_interviews.md")
elif page == "Mastery Checklist":
    markdown_page("CHECKLIST", "Mastery Checklist", "Only tick the items you can really do on your own.", "mastery_checklist.md")
elif page == "10-Week Plan":
    markdown_page("PLAN", "10-Week Study Plan", "A fixed daily rhythm, so you never have to decide on the spot what to study today.", "weekly_plan.md")
elif page == "Settings":
    settings_page()

if page != "Lessons":
    st.session_state.pop("_shown_lesson", None)

# Page-level scripts go in the sidebar so their (invisible) frames add no gap to the lesson itself.
with st.sidebar:
    import streamlit.components.v1 as components
    components.html(EDITOR_KEYS_JS, height=0)
    _scroll = st.session_state.pop("_scroll_top", None)
    if _scroll:
        components.html(SCROLL_TOP_JS % _scroll, height=0)
