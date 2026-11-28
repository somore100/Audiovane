"""Write microphone phrases to one WAV file per session (standard library only).

Used by the Speech-to-Text panel's "Save recording" option. The file is created on the
first phrase (so a session with no speech leaves nothing behind), never replaces an
existing file, and its header is kept valid after every write, so a crash or a killed app
still leaves a playable recording.
"""
import os
import time
import wave

GAP_SECONDS = 0.3          # silence kept between phrases


class PhraseRecorder:
    def __init__(self, folder):
        self.folder = os.path.expanduser(folder)
        self.path = None
        self.rate = 0
        self.frames = 0
        self._w = None

    def write(self, raw, rate):
        """Append 16-bit mono PCM `raw` recorded at `rate` Hz, followed by a short pause."""
        if self._w is None:
            os.makedirs(self.folder, exist_ok=True)
            base = os.path.join(self.folder, time.strftime("recording_%Y%m%d_%H%M%S"))
            path, n = base + ".wav", 2
            while os.path.exists(path):
                path, n = f"{base}_{n}.wav", n + 1
            self._w = wave.open(path, "wb")
            self._w.setnchannels(1)
            self._w.setsampwidth(2)
            self._w.setframerate(int(rate))
            self.path, self.rate = path, int(rate)
        gap = b"\x00\x00" * int(self.rate * GAP_SECONDS)
        self._w.writeframes(raw + gap)
        self.frames += (len(raw) + len(gap)) // 2

    def close(self):
        """Finish the file. Returns (path, seconds), or None when nothing was written."""
        if self._w is None:
            return None
        self._w.close()
        self._w = None
        return self.path, self.frames / float(self.rate)
