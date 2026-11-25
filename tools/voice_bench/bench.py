"""Generate new sentences in your voice with an engine and score them.

    python tools/voice_bench/bench.py DATASET --engine xtts
    options: --refs 06,15,30   --seeds 1   --limit 5   --floor am_adam,bm_george   --blind

DATASET is a folder made by prep.py. For every reference set (refs/ref_XXs.wav) x
sentence x seed the engine speaks the sentence in the reference voice; each result is
scored against the held-out real clips (see score.py) and timed. The table at the end
shows, per reference length: mean / worst speaker similarity, f0, real-time factor and
speed, next to the real-voice CEILING and any FLOOR voices (ordinary Kokoro voices,
to show that pitch alone is not identity).

Output (inside DATASET): gen/<engine>/<ref>/s<N>_seed<M>.wav, results_<engine>.json, and
with --blind a shuffled listen/ folder (A01.wav ...) plus listen/key.json for an
unbiased listening test: listen first, open key.json after.

Engines are small functions in ENGINES below: add one (F5-TTS, Chatterbox ...) that
returns synth(text, ref_wav, out_path, seed) and the rest works unchanged.
XTTS-v2 must already be installed from the app (that is where its CPML license
dialog is shown); this tool never accepts a license for you.
"""
import argparse
import glob
import json
import os
import random
import shutil
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))     # repo root, for the Kokoro floor
import common  # noqa: E402
import score   # noqa: E402

SENTENCES = [
    "Please remind me to call the dentist on Thursday morning, and then pick up the parcel from the post office.",
    "Wait, did you really say that the meeting was moved to next week?",
    "The old lighthouse stood at the edge of the cliff, and every evening, as the sun sank into the sea, "
    "its lamp slowly turned and swept the dark water.",
    "I can't believe it worked on the very first try!",
    "Number seven is the one I'd choose, but only if the price stays under forty dollars.",
]


def _seed(n):
    import torch
    random.seed(n)
    np.random.seed(n)
    torch.manual_seed(n)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(n)


def make_xtts():
    import torch
    import torch.serialization
    try:
        from trainer.io import get_user_data_dir
        cache = str(get_user_data_dir("tts"))
    except Exception:
        cache = os.path.expanduser("~/.local/share/tts")
    if not any("xtts_v2" in d for d in (os.listdir(cache) if os.path.isdir(cache) else [])):
        sys.exit("XTTS-v2 is not installed. Open Audiovane > Models and download it first "
                 "(that shows the license dialog).")
    os.environ["COQUI_TOS_AGREED"] = "1"          # already accepted in the app when it was downloaded
    try:
        from TTS.tts.configs.xtts_config import XttsConfig
        torch.serialization.add_safe_globals([XttsConfig])
    except Exception:
        pass
    from engines.coqui_xtts import patch_torchaudio_load      # same torchcodec workaround as the app
    patch_torchaudio_load()
    from TTS.api import TTS
    dev = common.device()
    print(f"loading XTTS-v2 on {dev} ...")
    tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=False).to(dev)

    def synth(text, ref_wav, out_path, seed):
        _seed(seed)
        tts.tts_to_file(text=text, language="en", speaker_wav=ref_wav, file_path=out_path)
    return synth


ENGINES = {"xtts": make_xtts}


def make_floor(voices, outdir):
    """Ordinary non-cloned Kokoro speech: the 'pitch matches but it is not you' control."""
    out = {}
    try:
        from engines import kokoro
        spec = kokoro.build(os.path.join(os.path.dirname(os.path.dirname(HERE)), "models"))
        for v in voices:
            p = os.path.join(outdir, f"floor_{v}.wav")
            spec.synthesize(SENTENCES[0], v, p, "en")
            out[v] = p
    except Exception as e:                      # noqa: BLE001
        print(f"  (floor voices skipped: {e})")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dataset")
    ap.add_argument("--engine", default="xtts", choices=sorted(ENGINES))
    ap.add_argument("--refs", default="", help="e.g. 06,15,30 (default: every refs/ref_*.wav)")
    ap.add_argument("--seeds", type=int, default=1)
    ap.add_argument("--limit", type=int, default=len(SENTENCES), help="use only the first N sentences")
    ap.add_argument("--floor", default="", help="Kokoro voices as the floor, e.g. am_adam,bm_george")
    ap.add_argument("--blind", action="store_true", help="also write a shuffled listen/ folder")
    a = ap.parse_args()

    ds = os.path.expanduser(a.dataset)
    refs = sorted(glob.glob(os.path.join(ds, "refs", "ref_*.wav")))
    if a.refs:
        want = {f"ref_{int(x):02d}s.wav" for x in a.refs.split(",")}
        refs = [r for r in refs if os.path.basename(r) in want]
    if not refs:
        sys.exit("no reference sets found (run prep.py first)")
    held_files = sorted(glob.glob(os.path.join(ds, "heldout", "*.wav")))
    if len(held_files) < 2:
        sys.exit("need at least 2 clips in DATASET/heldout")

    print(f"speaker model on {common.device()} ...")
    held = [score.embed(common.load_audio(f)) for f in held_files]
    centroid = np.mean(held, axis=0)
    ceil = np.mean([score.cos(e, np.mean([h for j, h in enumerate(held) if j != i], axis=0))
                    for i, e in enumerate(held)])

    synth = ENGINES[a.engine]()
    sents = SENTENCES[:a.limit]
    results, gens = [], []
    for ref in refs:
        rname = os.path.splitext(os.path.basename(ref))[0]
        rsec = len(common.load_audio(ref)) / common.SR_ANALYSIS
        for si, text in enumerate(sents, 1):
            for seed in range(a.seeds):
                out = os.path.join(ds, "gen", a.engine, rname, f"s{si}_seed{seed}.wav")
                os.makedirs(os.path.dirname(out), exist_ok=True)
                t0 = time.time()
                synth(text, ref, out, seed)
                took = time.time() - t0
                y = common.load_audio(out)
                dur = len(y) / common.SR_ANALYSIS
                st = common.f0_stats(y)
                r = {"ref": rname, "ref_seconds": round(rsec, 1), "sentence": si, "seed": seed,
                     "file": os.path.relpath(out, ds), "similarity": round(score.cos(score.embed(y), centroid), 4),
                     "f0_median": st["median"] if st else None, "seconds": round(dur, 2),
                     "words_per_sec": round(len(text.split()) / dur, 2), "rtf": round(took / dur, 2)}
                results.append(r)
                gens.append(out)
                print(f"  {rname} s{si} seed{seed}: sim {r['similarity']:.3f}  f0 {r['f0_median']}  "
                      f"rtf {r['rtf']}  ({took:.0f}s)")

    floors = {}
    if a.floor:
        for v, p in make_floor([x.strip() for x in a.floor.split(",") if x.strip()], os.path.join(ds, "gen")).items():
            y = common.load_audio(p)
            st = common.f0_stats(y)
            floors[v] = {"similarity": round(score.cos(score.embed(y), centroid), 4),
                         "f0_median": st["median"] if st else None}

    held_f0 = common.f0_stats(np.concatenate([common.load_audio(f) for f in held_files]))
    print(f"\n=== {a.engine}: {len(sents)} sentences x {a.seeds} seed(s), device {common.device()} ===")
    print(f"CEILING (real you, held-out vs held-out): {ceil:.3f}      real f0 median {held_f0['median']} Hz")
    print(f"{'reference':12s} {'ref s':>6s} {'mean sim':>9s} {'worst':>7s} {'vs ceil':>8s} {'f0':>6s} {'rtf':>5s} {'w/s':>5s}")
    for rname in sorted({r['ref'] for r in results}):
        rs = [r for r in results if r['ref'] == rname]
        sims = [r['similarity'] for r in rs]
        f0s = [r['f0_median'] for r in rs if r['f0_median']]
        print(f"{rname:12s} {rs[0]['ref_seconds']:6.1f} {np.mean(sims):9.3f} {np.min(sims):7.3f} "
              f"{np.mean(sims) - ceil:+8.3f} {np.mean(f0s):6.0f} {np.mean([r['rtf'] for r in rs]):5.2f} "
              f"{np.mean([r['words_per_sec'] for r in rs]):5.2f}")
    for v, f in floors.items():
        print(f"FLOOR {v:10s} (not cloned)    {f['similarity']:9.3f}               {f['f0_median']} Hz")
    print("\nHigher similarity = closer to you, but listen too: the score cannot judge accent or rhythm.")

    with open(os.path.join(ds, f"results_{a.engine}.json"), "w", encoding="utf-8") as f:
        json.dump({"engine": a.engine, "device": common.device(), "ceiling": round(float(ceil), 4),
                   "real_f0_median": held_f0["median"], "floors": floors, "results": results}, f, indent=2)

    if a.blind:
        ld = os.path.join(ds, "listen")
        shutil.rmtree(ld, ignore_errors=True)
        os.makedirs(ld)
        items = [(p, "generated") for p in gens] + [(p, "floor") for p in
                 (os.path.join(ds, "gen", f"floor_{v}.wav") for v in floors)] + \
                [(f, "real") for f in held_files[:3]]
        random.shuffle(items)
        key = {}
        for i, (p, kind) in enumerate(items, 1):
            name = f"A{i:02d}.wav"
            shutil.copy(p, os.path.join(ld, name))
            key[name] = {"kind": kind, "source": os.path.relpath(p, ds)}
        with open(os.path.join(ld, "key.json"), "w", encoding="utf-8") as f:
            json.dump(key, f, indent=2)
        print(f"\nBlind listening set: {ld}  ({len(items)} clips). Rate each A*.wav 1-5 for 'sounds like me',")
        print("then open key.json to see what was what.")


if __name__ == "__main__":
    main()
