"""Turns voices into sound: one thread (and one sox process) per note."""

from __future__ import annotations

import math
import shutil
import subprocess
import threading

from .instruments import Instrument, Voice

# Headroom per note so several simultaneous notes don't clip when mixed.
NOTE_PEAK_DB = -9.0


class SoxBackend:
    """Renders a :class:`Voice` with sox's ``play`` command."""

    executable = "play"

    def available(self) -> bool:
        return shutil.which(self.executable) is not None

    def command(self, voice: Voice, volume: float) -> list[str]:
        cmd = [self.executable, "-q", "-n", "synth", f"{voice.duration:g}"]
        for partial in voice.partials:
            cmd += [partial.waveform, f"{partial.frequency:.3f}"]
        # synth creates one channel per partial; fold them into one weighted mono mix.
        mix = ",".join(f"{i}v{p.gain:.4f}" for i, p in enumerate(voice.partials, 1))
        cmd += ["remix", mix]
        cmd += ["fade", "q", f"{voice.attack:g}", f"{voice.duration:g}", f"{voice.release:g}"]
        if voice.tail:
            cmd += ["pad", "0", f"{voice.tail:g}"]
        if voice.reverb:
            cmd += ["reverb", str(voice.reverb)]
        cmd += ["gain", "-n", f"{NOTE_PEAK_DB + 20 * math.log10(volume):.2f}"]
        return cmd


class NotePlayer:
    """Plays notes concurrently; every note runs on its own thread."""

    def __init__(self, backend: SoxBackend | None = None) -> None:
        self.backend = backend or SoxBackend()
        self._processes: set[subprocess.Popen] = set()
        self._lock = threading.Lock()
        self._closed = False

    def play(
        self, instrument: Instrument, frequency: float, duration: float, volume: float
    ) -> threading.Thread | None:
        """Start a note and return immediately. ``volume`` is 0.0-1.0."""
        if volume <= 0 or self._closed:
            return None
        command = self.backend.command(instrument.voice(frequency, duration), volume)
        thread = threading.Thread(target=self._run, args=(command,), daemon=True)
        thread.start()
        return thread

    def _run(self, command: list[str]) -> None:
        with self._lock:
            if self._closed:
                return
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._processes.add(process)
        try:
            process.wait()
        finally:
            with self._lock:
                self._processes.discard(process)

    @property
    def active_notes(self) -> int:
        with self._lock:
            return len(self._processes)

    def stop_all(self) -> None:
        with self._lock:
            processes = list(self._processes)
        for process in processes:
            process.terminate()

    def close(self) -> None:
        with self._lock:
            self._closed = True
        self.stop_all()
