"""Mutual exclusion and status for the arXiv harvest.

The harvest used to run as a thread spawned inside a gunicorn worker by
/update. That starved request handling: with two sync workers, a harvest
holding the GIL made every request routed to its worker crawl, and pages
needing no database at all timed out. It runs in its own process now (see
harvest.py), driven by the cron container; the web app only reads status.

Mutual exclusion is an flock around a small JSON file. A claim records the
process holding it so a claim whose holder died can be taken over -- without
that, a harvest killed mid-run left `running: true` forever and every later
attempt was refused, which stranded the feed for 46 days in Sep-Oct 2026.
"""

import datetime
import fcntl
import json
import os
import socket

STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          'tmp', 'update_state.json')
LOCK_FILE = STATE_FILE + '.lock'

DEFAULT_STATE = {'running': False, 'started': None, 'finished': None, 'count': None,
                 'error': None, 'pid': None, 'host': None}

# Backstop for a holder that is alive but whose harvest is wedged. Generous
# because a first harvest walks the whole archive and legitimately runs for
# hours; a daily incremental run takes minutes.
STALE_AFTER = datetime.timedelta(hours=12)


def read_state():
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(DEFAULT_STATE)


def write_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    tmp = STATE_FILE + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(state, f)
    os.replace(tmp, STATE_FILE)


def holder_alive(state):
    """Is the process that claimed the slot still running?

    Only answerable from the same container: pids are per-namespace, so a pid
    from another container would be checked against an unrelated process here.
    When the claim came from elsewhere we say "alive" and let the wall-clock
    backstop decide, rather than taking over a claim that may well be active.
    """
    pid = state.get('pid')
    if not pid:
        return False
    host = state.get('host')
    if host and host != socket.gethostname():
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def claim_is_stale(state):
    """True when a 'running' claim should be ignored and taken over."""
    if not holder_alive(state):
        return True
    try:
        age = datetime.datetime.now() - datetime.datetime.fromisoformat(state.get('started'))
    except (TypeError, ValueError):
        # Unparseable start time means we can't age the claim, so treat it as
        # stale rather than block on it forever.
        return True
    return age > STALE_AFTER


def claim_slot(logger=None):
    """Atomically mark a harvest as running. Returns (claimed, state)."""
    os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
    with open(LOCK_FILE, 'w') as lockf:
        fcntl.flock(lockf, fcntl.LOCK_EX)
        state = read_state()
        if state.get('running'):
            if not claim_is_stale(state):
                return False, state
            if logger:
                logger.warning('taking over stale harvest claim (started=%s pid=%s host=%s)',
                               state.get('started'), state.get('pid'), state.get('host'))
        state = {
            'running': True,
            'started': datetime.datetime.now().isoformat(),
            'finished': None,
            'count': None,
            'error': None,
            'pid': os.getpid(),
            'host': socket.gethostname(),
        }
        write_state(state)
        return True, state


def finish_slot(count=None, error=None, logger=None):
    with open(LOCK_FILE, 'w') as lockf:
        fcntl.flock(lockf, fcntl.LOCK_EX)
        state = read_state()
        if state.get('pid') not in (None, os.getpid()):
            # Our claim was taken over as stale and someone else is running.
            # Clearing it here would mark their live harvest finished.
            if logger:
                logger.warning('finished late; claim now held by pid %s, leaving it',
                               state.get('pid'))
            return
        state['running'] = False
        state['pid'] = None
        state['host'] = None
        state['finished'] = datetime.datetime.now().isoformat()
        state['count'] = count
        state['error'] = error
        write_state(state)


def status():
    """State plus whether a 'running' claim is one the next caller would take."""
    state = read_state()
    state['stale'] = bool(state.get('running')) and claim_is_stale(state)
    return state
