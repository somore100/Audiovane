"""Score generated speech against held-out recordings of the real voice.

    python tools/voice_bench/score.py DATASET_DIR  gen1.wav gen2.wav ...
    python tools/voice_bench/score.py DATASET_DIR  --ceiling        # real-vs-real only

DATASET_DIR is the folder prep.py made (it holds heldout/). For every generated
file it prints
  * speaker similarity: cosine similarity of WavLM speaker embeddings between the
    generated speech and the held-out clips of the real voice (higher = more like
    you). Compare it with the CEILING (held-out clip vs the other held-out clips:
    how similar the real you is to itself) and with the FLOOR you provide as
    ordinary non-cloned speech, e.g. a preset voice shifted to your pitch.
  * f0 median / range, as context only: matching pitch does NOT mean matching voice.

The speaker model is microsoft/wavlm-base-plus-sv via `transformers` (already an
Audiovane dependency); the first run downloads about 380 MB. Runs on CPU.
This number is a proxy. Final judgement is a blind listening test.
"""
import argparse
import glob
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

_MODEL = None


def _embedder():
    global _MODEL
    if _MODEL is None:
        import torch
        from transformers import AutoFeatureExtractor, WavLMForXVector
        name = "microsoft/wavlm-base-plus-sv"
        fe = AutoFeatureExtractor.from_pretrained(name)
        m = WavLMForXVector.from_pretrained(name).eval().to(common.device())
        _MODEL = (torch, fe, m)
    return _MODEL


def embed(y):
    torch, fe, m = _embedder()
    inp = fe(y, sampling_rate=common.SR_ANALYSIS, return_tensors="pt", padding=True)
    inp = {k: v.to(common.device()) for k, v in inp.items()}
    with torch.no_grad():
        e = m(**inp).embeddings
    e = torch.nn.functional.normalize(e, dim=-1)[0]
    return e.cpu().numpy()


def cos(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dataset")
    ap.add_argument("generated", nargs="*")
    ap.add_argument("--ceiling", action="store_true", help="only print the real-vs-real ceiling")
    a = ap.parse_args()

    held_files = sorted(glob.glob(os.path.join(os.path.expanduser(a.dataset), "heldout", "*.wav")))
    if len(held_files) < 2:
        sys.exit("need at least 2 clips in DATASET/heldout (run prep.py first)")
    print(f"{len(held_files)} held-out clips; loading speaker model on {common.device()} ...")
    held = [embed(common.load_audio(f)) for f in held_files]

    # ceiling: each held-out clip against the mean of the others
    ceil = []
    for i, e in enumerate(held):
        others = np.mean([h for j, h in enumerate(held) if j != i], axis=0)
        ceil.append(cos(e, others))
    print(f"\nCEILING (real you vs your other held-out clips): mean {np.mean(ceil):.3f}  "
          f"min {np.min(ceil):.3f}  max {np.max(ceil):.3f}")
    if a.ceiling or not a.generated:
        return

    centroid = np.mean(held, axis=0)
    print(f"\n{'file':45s} {'similarity':>10s} {'vs ceiling':>10s}   f0 median (p5-p95)")
    for f in a.generated:
        y = common.load_audio(f)
        s = cos(embed(y), centroid)
        st = common.f0_stats(y)
        f0 = f"{st['median']:.0f} Hz ({st['p5']:.0f}-{st['p95']:.0f})" if st else "n/a"
        print(f"{os.path.basename(f)[:45]:45s} {s:10.3f} {s - np.mean(ceil):+10.3f}   {f0}")


if __name__ == "__main__":
    main()
