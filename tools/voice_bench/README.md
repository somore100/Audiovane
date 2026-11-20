# Voice benchmark tools

Small command-line tools for judging how close a TTS engine gets to *your* voice (identity,
not just pitch). They are not part of the app and import nothing from it.
Your recordings are personal data: output defaults to `~/.local/share/audiovane/voice_bench/`,
outside the repository.

Run from the project venv (Python 3.12). Both tools work on CPU; CUDA is used when present.

## 1. Prepare a dataset from one recording

```bash
python tools/voice_bench/prep.py "path/to/recording.m4a"        # m4a/mp3 need ffmpeg on PATH
```

Splits at pauses into clips, transcribes with Whisper (`--whisper-model small.en`, first run
downloads it), scores each clip, builds nested reference sets `refs/ref_06s.wav`, `ref_15s.wav`,
`ref_30s.wav` from the cleanest clips, and keeps every other clip in `heldout/`. The engines never
see `heldout/`; it is the real voice the generated speech is scored against.
Read `transcripts.txt` and fix wrong words in `manifest.json` (reference transcripts matter for F5-TTS).

## 2. Score generated speech

```bash
python tools/voice_bench/score.py ~/.local/share/audiovane/voice_bench/NAME gen1.wav gen2.wav
```

Prints the speaker similarity (WavLM x-vector cosine, higher is closer) of each generated file to the
held-out clips, next to the **ceiling** (the real voice against its own other clips). Add a **floor**
of ordinary speech (a stock preset voice, ideally one with a similar pitch) to show that matching pitch
is not matching identity. First run downloads `microsoft/wavlm-base-plus-sv` (~380 MB).

The score is a proxy: finish with a blind listening comparison.

## Suggested experiment

For each engine (XTTS-v2, F5-TTS, Chatterbox, ...): generate the same 5 new sentences from each
`refs/*.wav` (3 seeds), score them, and compare against the ceiling and the floor.

## 3. Generate and score with an engine

```bash
python tools/voice_bench/bench.py ~/.local/share/audiovane/voice_bench/NAME --engine xtts --floor am_adam,bm_george --blind
```

Speaks 5 new sentences from each reference set, scores them against the held-out clips and prints one
table (similarity, f0, speed, real-time factor) next to the ceiling and the floor voices. `--blind`
writes a shuffled `listen/` folder: rate each clip by ear first, then open `listen/key.json`.
`--refs 06,30 --limit 2 --seeds 3` narrow or widen the run. XTTS-v2 must already be downloaded in the app.
Other engines plug in as one function in `ENGINES` (see the file).
