"""Run from tests/: <venv python> -B -m unittest -v test_captions"""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import subtitles


def _words(texts, step=0.3):
    out, t = [], 0.0
    for w in texts:
        out.append({"word": " " + w, "start": t, "end": t + step * 0.8})
        t += step
    return out


class CaptionTests(unittest.TestCase):
    def test_no_words_are_lost(self):
        rnd = random.Random(7)
        vocab = ["a", "to", "extraordinarily", "the", "interesting", "of", "understanding",
                 "it", "wonderful", "and", "responsibilities", "in", "I"]
        for _ in range(300):
            ws = [rnd.choice(vocab) for _ in range(rnd.randint(1, 60))]
            caps = subtitles.chunk_into_captions(_words(ws))
            got = " ".join(c["text"] for c in caps).split()
            self.assertEqual(got, ws)

    def test_cards_respect_the_line_limits_and_stay_in_order(self):
        ws = ["extraordinarily"] * 20
        caps = subtitles.chunk_into_captions(_words(ws))
        for c in caps:
            self.assertLessEqual(len(c["text"].split("\n")), 2)
            self.assertLessEqual(c["start"], c["end"])
        for a, b in zip(caps, caps[1:]):
            self.assertLessEqual(a["end"], b["start"] + 1e-9)


if __name__ == "__main__":
    unittest.main()
