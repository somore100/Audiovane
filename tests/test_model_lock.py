"""The window and the Local API share one model lock. Run from tests/: <venv python> -B -m unittest -v test_model_lock"""
import os
import sys
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import api_server
import model_lock
from engines import registry
from engines.base import EngineSpec


def _spec(synth):
    return EngineSpec(key="fake", display_name="Fake", approx_size="0", description="",
                      license="", requires_tos=False, tos_title="", tos_text="",
                      is_installed=lambda: True, download=lambda cb=None: None,
                      list_voices=lambda: ["a"], synthesize=synth)


class ModelLockTests(unittest.TestCase):
    def test_api_uses_the_shared_lock(self):
        api = api_server.ApiServer(object(), 0, "avs-test-key-0123456789")
        self.assertIs(api._lock, model_lock.LOCK)

    def test_engine_calls_never_overlap(self):
        active, worst = [0], [0]

        def synth(*a, **kw):
            active[0] += 1
            worst[0] = max(worst[0], active[0])
            time.sleep(0.05)
            active[0] -= 1
        spec = registry._shared(_spec(synth))
        ts = [threading.Thread(target=spec.synthesize, args=("t", "v", "o.wav")) for _ in range(6)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(worst[0], 1)

    def test_api_request_can_call_engine_without_deadlock(self):
        spec = registry._shared(_spec(lambda *a, **kw: None))
        done = []

        def job():
            with model_lock.LOCK:               # what an API request holds
                spec.synthesize("t", "v", "o.wav")
                done.append(1)
        t = threading.Thread(target=job)
        t.start()
        t.join(2)
        self.assertEqual(done, [1])


if __name__ == "__main__":
    unittest.main()
