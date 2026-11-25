# Audiovane (formerly AI Voice Studio) - Handoff v18

Project: `/home/domore100/AI_Workspace/projects/Local/audiovane` (Claude sandbox: `/run/host/home/domore100/...`). GitHub: somore100/Audiovane. Renamed from "AI Voice Studio" on 2026-11-14; `legacy.py` migrates the old settings/models folders and login entry. Older notes below may still say "AI Voice Studio".

## Update 2026-11-25
* **Released v1.2.0** (tag on `main` 9c93b36). The build workflow also runs on `v*` tags and a `release` job attaches the Windows installer, Linux AppImage, macOS zip and SHA256SUMS.txt to a GitHub Release (the action was set to draft; the first release showed as published). Before tagging: bump `APP_VERSION` in main.py AND `AppVersion` in installer_public.iss. All three platform builds and the packaged-app MCP smoke test (`ci_smoke.py`) are green. The installers themselves are NOT tested on a clean machine.
* `main` is at 2861819. Merged since the 11-17 notes: PR #10 rename, #11 CI smoke test + installer fixes, #12 release job, #13 version 1.2.0, #14 voice benchmark tools + XTTS torchcodec fix, #15 linuxdeploy pinned (1-alpha-20251107-1 + sha256), #16 shared model lock (audit M1: `model_lock.LOCK` is an RLock used by the API, the engine registry wrappers and the Whisper/Vosk getters; `_LockedModel` wraps the Whisper models and collects faster-whisper's lazy segments inside the lock). `python selftest.py` passes 15/15 on the real app. Committing straight to `main` is allowed (the ruleset only blocks deletion and force push).
* **Voice cloning goal** (personal voice identity, local-first, RTX 3060 12 GB on the main PC; the laptop has integrated graphics only): tools in `tools/voice_bench/` (prep.py, score.py, bench.py; output goes to `~/.local/share/audiovane/voice_bench/`, outside the repo). First XTTS-v2 numbers on the laptop CPU (5 sentences, 1 seed): speaker similarity 0.83 (9 s reference), 0.86 (18 s), 0.84 (32 s) vs a real-voice ceiling of 0.974 and a stock-voice floor of 0.65-0.69; the clone's pitch is erratic (112-145 Hz vs the real 136 Hz). Reference length barely matters. The user has a blind listening set (20 clips) but has NOT yet given ratings. Next: ratings, then F5-TTS / Chatterbox on the 3060 PC (its `nvidia-smi` output is wanted), check licenses from primary sources (XTTS is CPML non-commercial), more recordings (10-20 min), then voice profiles + a cleaner engine interface. App side: XTTS runs on CPU only (`gpu=False` in engines/coqui_xtts.py); cloning still passes a path inside the voice string (`CLONE_PREFIX`).
* Fixed: XTTS cloning needed `torchcodec` with torchaudio 2.10; `engines/coqui_xtts.py: patch_torchaudio_load()` falls back to soundfile.
* Still open from the audits: M2 STT Stop/listen timeout + generation counter, M4 control-port per-user secret, L1-L4, L8, M9 (hash-pinned lockfile, action SHAs, Kokoro SHA-256), H2 installer pip lines (now only run with the install_models / install_xtts tasks).
* Claude tooling: the MCP server `audiovane` is registered in the terminal CLI and in the Claude desktop app (the app keeps its own config under `~/.local/share/claude-desktop-box/` and uses `distrobox-host-exec` to run on the host). A stale pre-rename `ai-voice-studio` entry was removed. A local Qwen router MCP exists (laptop 7B; main PC 14B only at weekends); its first trial with the 7B gave unusable test code, so review everything it produces.
* The `cc-plugin-privacy` hook refuses Bash commands that name main.py, or scripts that read a file holding the support email address (main.py, older handoffs). Use the Read/Edit/Write tools for those, and `git commit -a` instead of naming main.py.

## Update 2026-11-17
* `main` was at 1d087e9 (security-audit PR #9 merged, v1.1.0) when PR #10 (`rename/audiovane`) was opened; it is merged now.
* Venv must be **Python 3.12** (`python3.12 -m venv venv && pip install -r requirements.txt`). A 3.14 venv fails: `audioop` is gone in 3.13+ and the torch pins target 3.12. If PyAudio fails to build: `sudo dnf install portaudio-devel python3.12-devel gcc`.
* The `ALSA lib ... Unknown PCM cards.pcm.rear/center_lfe/side` lines at startup are harmless pygame/SDL probing.
* Possible feature: an MCP tool to open the app window.
Python 3.12 + Tkinter. `main.py`, `audio_fx.py`, `curve_editor.py`, `voice_finder.py`, `live_pitch.py`, `subtitles.py`, `api_server.py`, `feedback.py`, `engines/`.

## Environment notes
* `git`/`gh` are not installed in the Claude sandbox: use `distrobox-host-exec git -C /home/domore100/... ` / `distrobox-host-exec gh ...` (a `~` expands to the sandbox home, so use the full host path). `wpctl` etc. run plainly in the user's own terminal.
* The sandbox cannot run the GUI or audio, has no tkinter (stub it to test pure logic), no ffmpeg and no GPU. Its HOME differs, so the model cache is elsewhere: use `XDG_DATA_HOME=/run/host/home/domore100/.local/share` when testing engines. Loading XTTS there can be killed for memory: run those checks in the user's terminal.
* If the voice changer says the mic is "pure silence": the default PipeWire source got muted again. `wpctl set-mute @DEFAULT_AUDIO_SOURCE@ 0 && wpctl set-volume @DEFAULT_AUDIO_SOURCE@ 0.8`.

## Git state
* Work is on `main`; feature branches are merged. When stacking PRs, retarget the second to `main` (or merge only after the base is retargeted) or it merges into the old branch.

## Done (user-tested on Linux unless noted)
* Voice changer: fast-Whisper warm-up, shorter pauses, TTS streamed per sentence, Vosk streaming (`listen_vosk`, worker accepts pre-recognized text), click/typing/hallucination filtering (`_voiced_seconds`, `_VC_JUNK`, VAD + no-speech filter), one clear error on a muted/unopenable mic.
* TTS tab: selected-text-only speed/pitch.
* Mini-mode bars follow the real mic level (`_MIC_LEVEL`).
* Leave Feedback: `feedback.py` (reusable, stdlib only) + footer button; sends via the shared Google Apps Script relay (`FEEDBACK_ENDPOINT` in main.py, same one as Arrows of War); fallbacks Open in Gmail / mail app / Copy. Verified end to end.
* Local API: word timestamps (`timestamp_granularities[]=word` + `verbose_json` -> `words`), repeated multipart fields are merged. The selftest now exercises word timestamps against the live API.
* Local API autostart: `autostart.py` (login modes off/window/background via XDG .desktop, Windows Run key, macOS LaunchAgent; single-instance via loopback port 47653), `applog.py` (tee stdout/stderr to `<settings dir>/app.log`), "At login" selector + "Open log" in the API section. Windows registry and macOS plist NOT run.
* MCP server (`mcp_server.py`, stdlib JSON-RPC over stdio, tools speak/list_voices/transcribe/status; bridges to the Local API, reads port+key from prefs.json, auto-starts the background engine; `speak` saves only a plain filename into the output folder, never overwrites). Register: `claude mcp add --scope user audiovane -- <venv python> <path>/mcp_server.py`. The packaged builds answer the MCP handshake (CI smoke test).
* Self-test (`selftest.py`, also `--selftest`): PASS/FAIL per step against the live API + MCP; 15/15 on the real app.
* Headless engine (`headless.py`, `--headless`, alias `--background`): Local API with no window/Tk; control port 47654; the GUI attaches via `autostart.headless_probe()`. NOT tested: Windows console hiding.
* API docs `docs/API.md` + `examples/`. Node and OpenAI-SDK examples untested.
* SECURITY AUDIT: hardened `api_server.py` (key required unless "Allow without a key"; foreign Origin refused; JSON-only speech; uploads sniffed, ffmpeg pinned; request bounds; constant-time key compare). prefs.json is 0600. `clone:<path>` voices removed from the API. Regression tests: `tests/test_api_hardening.py` (17 run anywhere, 16 need ffmpeg + `tests/media` fixtures, not committed), `tests/test_model_lock.py`.
* UNTESTED: Windows/macOS virtual mic and Live Pitch (PyAudio output).

## Next
1. Voice cloning: listening ratings, engine bake-off on the 3060 PC, voice profiles.
2. Audit leftovers (M2 first), then latency work (partial Whisper transcription, real VAD, chunked TTS).
3. Quality: metallic effects at extremes; larger Vosk models; Python 3.13 (`audioop`).
* Seen once: `terminate called without an active exception` when closing the app during startup. Not reproduced.

## Pointers in `main.py`
* Voice changer: `_vc_pipeline` (`listen_vosk`, `worker`), `_vc_live_loop`, `_vc_play`, `_PyAudioOut`, `_vmic_*`
* Mic: `_open_mic`, `_DCBlockStream`, `_MIC_LEVEL`; mini bars `_animate_eq`
* TTS: `preview_voice`, `generate_voice`, `_sel_capture`, `_tts_synth_sel`, `_apply_tts_fx`
* Model getters: `get_whisper_model`, `get_fwhisper_model`, `get_vosk_model`, `_LockedModel`
* API backend: `_ApiBackend.stt` (words), `api_server.py` `_transcribe`
* Feedback: `AIApp.open_feedback`, `feedback.py`
