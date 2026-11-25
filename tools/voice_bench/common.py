"""Shared helpers for the voice benchmark tools (no Audiovane imports)."""
import json
import os
import shutil
import subprocess

import numpy as np
import soundfile as sf

SR_ANALYSIS = 16000        # whisper / speaker model / f0 all work at 16 kHz


def device():
    """'cuda' when a usable NVIDIA GPU exists, else 'cpu'."""
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def load_audio(path, sr=SR_ANALYSIS):
    """Mono float32 samples at `sr`. wav/flac/ogg are read directly; anything else
    (m4a, mp3, ...) goes through ffmpeg when it is installed, else librosa."""
    import librosa
    ext = os.path.splitext(path)[1].lower()
    if ext not in (".wav", ".flac", ".ogg") and shutil.which("ffmpeg"):
        cmd = ["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]
        raw = subprocess.run(cmd, check=True, capture_output=True).stdout
        return np.frombuffer(raw, dtype=np.float32).copy()
    y, _ = librosa.load(path, sr=sr, mono=True)
    return y.astype(np.float32)


def save_wav(path, y, sr=SR_ANALYSIS):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    sf.write(path, y, sr, subtype="PCM_16")


def f0_stats(y, sr=SR_ANALYSIS):
    """Median / 5th / 95th percentile f0 in Hz plus its spread in semitones.
    Returns None when there is almost no voiced speech."""
    import librosa
    f0, _, _ = librosa.pyin(y, fmin=60, fmax=400, sr=sr, frame_length=1024)
    f = f0[~np.isnan(f0)]
    if len(f) < 10:
        return None
    med = float(np.median(f))
    return {"median": round(med, 1),
            "p5": round(float(np.percentile(f, 5)), 1),
            "p95": round(float(np.percentile(f, 95)), 1),
            "std_semitones": round(float(np.std(12 * np.log2(f / med))), 2),
            "voiced_frac": round(float(len(f) / len(f0)), 2)}


def clip_quality(y, sr=SR_ANALYSIS):
    """Cheap per-clip quality numbers used to pick the cleanest reference clips."""
    hop = int(sr * 0.02)
    rms = np.sqrt(np.maximum(
        np.convolve(y.astype(np.float64) ** 2, np.ones(hop * 2) / (hop * 2), "same")[::hop], 1e-12))
    db = 20 * np.log10(rms)
    return {"duration": round(len(y) / sr, 2),
            "peak": round(float(np.abs(y).max()), 3),
            "clipped": int((np.abs(y) > 0.99).sum()),
            "snr_db": round(float(np.percentile(db, 90) - np.percentile(db, 10)), 1)}


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
