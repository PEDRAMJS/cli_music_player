import unittest
from pathlib import Path

from note_player import sequencer
from note_player.notes import NOTE_KEY_MAP
from note_player.sequencer import NoteFileError, Step, note_frequency, parse

SONGS = Path(__file__).resolve().parent.parent / "songs"


class NoteFrequencyTest(unittest.TestCase):
    def test_names(self):
        self.assertAlmostEqual(note_frequency("a4"), 440.0)
        self.assertAlmostEqual(note_frequency("A3"), 220.0)
        self.assertAlmostEqual(note_frequency("c4"), NOTE_KEY_MAP["a"], places=1)
        self.assertAlmostEqual(note_frequency("c#4"), note_frequency("db4"))
        self.assertAlmostEqual(note_frequency("b#3"), note_frequency("c4"))

    def test_invalid(self):
        for token in ("h4", "a", "a#", "4a", "a44"):
            with self.assertRaises(ValueError, msg=token):
                note_frequency(token)


class ParseTest(unittest.TestCase):
    def test_format(self):
        steps = parse("a4 1.2\nx 1.2\n\n# comment\nc4 E4 g4 0.5  # chord\nf#4 .25\n")
        self.assertEqual([s.line for s in steps], [1, 2, 5, 6])
        self.assertEqual([s.duration for s in steps], [1.2, 1.2, 0.5, 0.25])
        self.assertEqual(steps[1].frequencies, ())
        self.assertEqual(len(steps[2].frequencies), 3)
        self.assertAlmostEqual(steps[3].frequencies[0], note_frequency("f#4"))

    def test_errors_name_the_line(self):
        cases = {"a4 1\nb4": "line 2", "a4 1\nh4 1": "line 2", "a4 fast": "line 1", "a4 0": "line 1"}
        for text, where in cases.items():
            with self.assertRaisesRegex(NoteFileError, where):
                parse(text)

    def test_bundled_songs_parse(self):
        for path in SONGS.glob("*.notes"):
            self.assertTrue(sequencer.load(path), path)


class PlayTest(unittest.TestCase):
    def setUp(self):
        self.steps = [Step((440.0,), 0.5, 1), Step((), 0.25, 2), Step((261.6, 329.6), 1.0, 3)]
        self.played, self.waits = [], []

    def test_plays_in_order_with_durations(self):
        finished = sequencer.play(
            self.steps, lambda f, d: self.played.append((f, d)), lambda s: self.waits.append(s) or True
        )
        self.assertTrue(finished)
        self.assertEqual(self.played, [(440.0, 0.5), (261.6, 1.0), (329.6, 1.0)])
        # The fake wait doesn't sleep, so each wait reaches for the next absolute deadline.
        for waited, deadline in zip(self.waits, (0.5, 0.75, 1.75)):
            self.assertAlmostEqual(waited, deadline, places=2)

    def test_wait_can_abort(self):
        finished = sequencer.play(self.steps, lambda f, d: self.played.append(f), lambda s: False)
        self.assertFalse(finished)
        self.assertEqual(self.played, [440.0])


if __name__ == "__main__":
    unittest.main()
