"""Turn one long recording into a small benchmark dataset.

    python tools/voice_bench/prep.py "voice recording test.m4a"
    python tools/voice_bench/prep.py rec.wav --out ~/voices/me --whisper-model small.en
    options: --ref-lengths 6,15,30   --min-clip 3 --max-clip 14   --no-transcribe

What it does
  1. Splits the recording at natural pauses into 3-14 s clips.
  2. Transcribes every clip with Whisper (check the text by hand afterwards:
     it is stored in manifest.json and transcripts.txt).
  3. Scores each clip (length, peak, clipped samples, rough SNR, f0).
  4. Picks the cleanest clips into nested reference sets (refs/ref_06s.wav,
     ref_15s.wav, ref_30s.wav ... each built from whole clips, so a bit longer
     than the nominal length). Every clip that is NOT in the largest reference
     set goes to heldout/ - the engines never see it, so it is the "real you"
     the generated speech is scored against.

Output goes outside the repository by default (your voice is personal data):
    ~/.local/share/audiovane/voice_bench/<recording name>/

Runs on CPU; uses CUDA for Whisper when available.
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402


def split_clips(y, sr, min_len, max_len, gap=0.3, top_db=35):
    """Clip boundaries (start, end) in seconds: whole phrases, cut at pauses >= gap."""
    import librosa
    iv = librosa.effects.split(y, top_db=top_db, frame_length=1024, hop_length=256)
    iv = [(s / sr, e / sr) for s, e in iv]
    clips, cur = [], None
    for s, e in iv:
        if cur is None:
            cur = [s, e]
        elif s - cur[1] < gap:                       # tiny pause inside a phrase: keep together
            cur[1] = e
        elif (cur[1] - cur[0]) < min_len and (e - cur[0]) <= max_len:
            cur[1] = e                               # clip still too short: join the next phrase
        else:
            clips.append(tuple(cur))
            cur = [s, e]
    if cur:
        clips.append(tuple(cur))
    out = [(max(0.0, s - 0.1), min(len(y) / sr, e + 0.1)) for s, e in clips]   # 0.1 s padding
    return [(s, e) for s, e in out if e - s >= 1.0]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audio")
    ap.add_argument("--out")
    ap.add_argument("--ref-lengths", default="6,15,30", help="nominal reference lengths in seconds")
    ap.add_argument("--min-clip", type=float, default=3.0)
    ap.add_argument("--max-clip", type=float, default=14.0)
    ap.add_argument("--whisper-model", default="small.en")
    ap.add_argument("--no-transcribe", action="store_true")
    a = ap.parse_args()

    stem = os.path.splitext(os.path.basename(a.audio))[0].replace(" ", "_")
    out = os.path.expanduser(a.out or f"~/.local/share/audiovane/voice_bench/{stem}")
    os.makedirs(out, exist_ok=True)

    print(f"loading {a.audio}")
    y = common.load_audio(a.audio)
    sr = common.SR_ANALYSIS
    print(f"  {len(y) / sr:.1f} s; whole-recording f0: {common.f0_stats(y)}")

    spans = split_clips(y, sr, a.min_clip, a.max_clip)
    print(f"  {len(spans)} clips")
    model = None
    if not a.no_transcribe:
        import whisper
        dev = common.device()
        print(f"loading Whisper '{a.whisper_model}' on {dev} (first run downloads it)")
        model = whisper.load_model(a.whisper_model, device=dev)

    clips = []
    for i, (s, e) in enumerate(spans, 1):
        seg = y[int(s * sr):int(e * sr)]
        name = f"clip_{i:03d}.wav"
        common.save_wav(os.path.join(out, "clips", name), seg, sr)
        text = ""
        if model is not None:
            text = model.transcribe(seg, language="en", fp16=(common.device() == "cuda"),
                                    condition_on_previous_text=False)["text"].strip()
        q = common.clip_quality(seg, sr)
        q["f0"] = common.f0_stats(seg, sr)
        clips.append({"file": f"clips/{name}", "start": round(s, 2), "end": round(e, 2),
                      "text": text, **q})
        print(f"  {name}  {q['duration']:5.1f}s  snr {q['snr_db']:4.1f}  clipped {q['clipped']:3d}  {text[:60]}")

    # ── nested reference sets from the cleanest clips ─────────────────────
    # clean = no clipping first, then highest SNR; very short or textless clips last
    order = sorted(range(len(clips)), key=lambda i: (clips[i]["clipped"] > 0, -clips[i]["snr_db"],
                                                     abs(clips[i]["duration"] - 8)))
    lengths = sorted(float(x) for x in a.ref_lengths.split(",") if x.strip())
    ref_sets, used = {}, []
    for target in lengths:
        total = sum(clips[i]["duration"] for i in used)
        for i in order:
            if total >= target:
                break
            if i not in used:
                used.append(i)
                total += clips[i]["duration"]
        chosen = sorted(used)                         # recording order sounds more natural
        wav = np.concatenate([np.concatenate([
            y[int(clips[i]["start"] * sr):int(clips[i]["end"] * sr)],
            np.zeros(int(0.25 * sr), dtype=np.float32)]) for i in chosen])
        fname = f"refs/ref_{int(target):02d}s.wav"
        common.save_wav(os.path.join(out, fname), wav, sr)
        ref_sets[fname] = {"clips": [clips[i]["file"] for i in chosen],
                           "seconds": round(len(wav) / sr, 1)}
        print(f"  {fname}: {len(chosen)} clips, {len(wav) / sr:.1f} s")

    held = [c for i, c in enumerate(clips) if i not in used]
    for c in clips:
        c["set"] = "reference" if c["file"] in {f for r in ref_sets.values() for f in r["clips"]} else "heldout"
    os.makedirs(os.path.join(out, "heldout"), exist_ok=True)
    for c in held:
        src = os.path.join(out, c["file"])
        dst = os.path.join(out, "heldout", os.path.basename(c["file"]))
        os.replace(src, dst)
        c["file"] = "heldout/" + os.path.basename(dst)

    common.write_json(os.path.join(out, "manifest.json"), {
        "source": os.path.abspath(a.audio), "sample_rate": sr, "whole_f0": common.f0_stats(y),
        "reference_sets": ref_sets, "clips": clips})
    with open(os.path.join(out, "transcripts.txt"), "w", encoding="utf-8") as f:
        for c in clips:
            f.write(f"[{c['set']}] {c['file']}\t{c['text']}\n")

    ho = sum(c["duration"] for c in held)
    print(f"\nDone -> {out}\n  reference clips: {len(clips) - len(held)}   held-out: {len(held)} clips, {ho:.1f} s")
    print("  Next: read transcripts.txt and fix any wrong words in manifest.json,")
    print("        then generate speech with each engine from refs/*.wav and run score.py.")
    if ho < 30:
        print("  Warning: under 30 s held out - similarity scores will be noisy. More recordings help.")


if __name__ == "__main__":
    main()
