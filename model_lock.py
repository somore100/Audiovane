"""One lock for every heavy model job, shared by the window and the Local API.

The speech and speech-to-text models are not thread-safe, and the window and the API
(which run on different threads) both use the same cached instances. Before this module
the API serialized its own jobs but the window did not, so a click in the window during
an API request could use a model while the other side was loading or running it.

It is an RLock: a job that already holds it (the API wraps a whole request) can call
code that takes it again without deadlocking.
"""
import functools
import threading

LOCK = threading.RLock()


def locked(fn):
    """Run fn while holding the shared model lock."""
    @functools.wraps(fn)
    def wrapper(*a, **kw):
        with LOCK:
            return fn(*a, **kw)
    return wrapper
