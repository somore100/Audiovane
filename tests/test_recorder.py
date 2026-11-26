"""Run from tests/: <venv python> -B -m unittest -v test_recorder"""
import os
import sys
import tempfile
import unittest
import wave

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import recorder


class RecorderTests(unittest.TestCase):
    def test_writes_a_valid_wav_with_gaps(self):
        with tempfile.TemporaryDirectory() as d:
            r = recorder.PhraseRecorder(os.path.join(d, "sub"))     # folder is created
            rate = 16000
            r.write(b"\x01\x00" * rate, rate)                        # 1 s
            # valid even before close (crash safety)
            with wave.open(r.path) as w:
                self.assertEqual(w.getframerate(), rate)
                self.assertEqual(w.getnframes(), rate + int(rate * 0.3))
            r.write(b"\x02\x00" * rate, rate)
            path, secs = r.close()
            self.assertAlmostEqual(secs, 2.6, places=2)
            with wave.open(path) as w:
                self.assertEqual((w.getnchannels(), w.getsampwidth()), (1, 2))
                self.assertEqual(w.getnframes(), 2 * rate + 2 * int(rate * 0.3))

    def test_no_speech_leaves_no_file(self):
        with tempfile.TemporaryDirectory() as d:
            r = recorder.PhraseRecorder(d)
            self.assertIsNone(r.close())
            self.assertEqual(os.listdir(d), [])

    def test_never_replaces_an_existing_file(self):
        with tempfile.TemporaryDirectory() as d:
            paths = []
            for _ in range(3):
                r = recorder.PhraseRecorder(d)
                r.write(b"\x00\x00" * 100, 8000)
                paths.append(r.close()[0])
            self.assertEqual(len(set(paths)), 3)
            self.assertEqual(len(os.listdir(d)), 3)


if __name__ == "__main__":
    unittest.main()
