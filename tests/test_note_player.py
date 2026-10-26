import os
import shutil
import subprocess
import unittest

from note_player import instruments
from note_player.engine import NotePlayer, SoxBackend
from note_player.instruments import Partial, Voice
from note_player.notes import NOTE_KEY_MAP, frequency_for, note_name
from note_player.settings import Settings


class NotesTest(unittest.TestCase):
    def test_map_is_chromatic(self):
        freqs = list(NOTE_KEY_MAP.values())
        for low, high in zip(freqs, freqs[1:]):
            self.assertAlmostEqual(high / low, 2 ** (1 / 12), places=3)

    def test_note_names(self):
        self.assertEqual(note_name(NOTE_KEY_MAP["a"]), "C4")
        self.assertEqual(note_name(NOTE_KEY_MAP["h"]), "A4")
        self.assertEqual(note_name(NOTE_KEY_MAP["'"]), "F5")

    def test_octave_shift_and_case(self):
        self.assertAlmostEqual(frequency_for("H", 1), 880.0)
        self.assertAlmostEqual(frequency_for("h", -1), 220.0)
        self.assertIsNone(frequency_for("q"))


class InstrumentsTest(unittest.TestCase):
    def test_defaults_are_discovered(self):
        self.assertIn("piano", instruments.available())
        self.assertIn("guitar", instruments.available())

    def test_unknown_instrument(self):
        with self.assertRaises(ValueError):
            instruments.create("kazoo")

    def test_voices_are_valid(self):
        for name in instruments.available():
            voice = instruments.create(name).voice(440.0, 1.0)
            self.assertIsInstance(voice, Voice)
            self.assertAlmostEqual(voice.partials[0].frequency, 440.0, delta=1.0)

    def test_piano_partials_are_stretched(self):
        partials = instruments.create("piano").voice(220.0, 1.0).partials
        self.assertGreater(partials[3].frequency, 4 * 220.0)

    def test_new_module_registers_itself(self):
        class Beep(instruments.Instrument):
            name = "test-beep"

            def voice(self, frequency, duration):
                return Voice((Partial(frequency),), duration)

        self.assertIsInstance(instruments.create("test-beep"), Beep)


class SoxBackendTest(unittest.TestCase):
    def test_command_shape(self):
        voice = Voice((Partial(440, 1.0), Partial(880, 0.5, "triangle")), 1.0, reverb=20, tail=0.3)
        cmd = SoxBackend().command(voice, 0.5)
        self.assertEqual(cmd[:5], ["play", "-q", "-n", "synth", "1"])
        self.assertIn("triangle", cmd)
        self.assertEqual(cmd[cmd.index("remix") + 1], "1v1.0000,2v0.5000")
        self.assertIn("reverb", cmd)

    @unittest.skipUnless(shutil.which("sox"), "sox not installed")
    def test_every_instrument_renders(self):
        env = {**os.environ, "AUDIODRIVER": "null"}
        for name in instruments.available():
            for key in ("a", "'"):
                cmd = SoxBackend().command(instruments.create(name).voice(NOTE_KEY_MAP[key], 0.3), 0.7)
                result = subprocess.run(["sox", *cmd[1:3], "-n", *cmd[3:]], capture_output=True, env=env)
                self.assertEqual(result.returncode, 0, f"{name}: {result.stderr.decode()}")


class PlayerTest(unittest.TestCase):
    def test_zero_volume_is_silent(self):
        self.assertIsNone(NotePlayer().play(instruments.create("piano"), 440, 1, 0))

    def test_notes_play_concurrently_and_stop(self):
        class SleepBackend(SoxBackend):
            def command(self, voice, volume):
                return ["sleep", "5"]

        player = NotePlayer(SleepBackend())
        piano = instruments.create("piano")
        threads = [player.play(piano, f, 3.0, 0.5) for f in (261.63, 329.63, 392.0)]
        for _ in range(100):
            if player.active_notes == 3:
                break
            threads[0].join(0.02)
        self.assertEqual(player.active_notes, 3)
        player.close()
        for thread in threads:
            thread.join(2)
            self.assertFalse(thread.is_alive())
        self.assertEqual(player.active_notes, 0)


class SettingsTest(unittest.TestCase):
    def test_clamping(self):
        settings = Settings()
        for _ in range(10):
            settings.shift_octave(1)
            settings.change_volume(1)
            settings.change_duration(-1)
        self.assertEqual((settings.octave_shift, settings.volume, settings.duration), (2, 100, 0.25))


if __name__ == "__main__":
    unittest.main()
