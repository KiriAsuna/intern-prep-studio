"""Stop the server once the last browser page has been closed.

Only active when started through the launcher (INTERN_PREP_AUTOSHUTDOWN=1), so running
`streamlit run app.py` by hand behaves as usual. All user data is written to disk on every
change, so exiting here cannot lose anything.
"""
import os
import threading
import time

GRACE_SECONDS = 12        # survives a page refresh or a short network blip
STARTUP_SECONDS = 180     # give up if no page ever connects

_started = False


def _watch():
    try:
        from streamlit.runtime import get_instance
        runtime = get_instance()
        count = runtime._session_mgr.num_active_sessions
    except Exception:
        return                      # unknown Streamlit internals: just never auto-exit
    started_at = time.time()
    seen_page = False
    idle_since = None
    while True:
        time.sleep(2)
        try:
            n = count()
        except Exception:
            return
        if n > 0:
            seen_page, idle_since = True, None
            continue
        if not seen_page:
            if time.time() - started_at > STARTUP_SECONDS:
                os._exit(0)
            continue
        idle_since = idle_since or time.time()
        if time.time() - idle_since > GRACE_SECONDS:
            os._exit(0)


def start(marker=None):
    """Called on every script run; `marker` is touched once so the launcher knows a page has connected."""
    global _started
    if _started or os.environ.get("INTERN_PREP_AUTOSHUTDOWN") != "1":
        return
    _started = True
    if marker is not None:
        try:
            marker.write_text(str(os.getpid()), encoding="utf-8")
        except OSError:
            pass
    threading.Thread(target=_watch, name="autoshutdown", daemon=True).start()
