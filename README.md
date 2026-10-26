# note_player

Play piano or guitar notes from your computer keyboard, in the terminal.

## Requirements

- Python 3.10+ (standard library only)
- [sox](https://sourceforge.net/projects/sox/) for audio: `sudo apt install sox`
- A POSIX terminal (Linux/macOS)

## Run

```sh
python3 main.py                       # menu
python3 main.py songs/twinkle.notes   # play a note file directly
```

Menu: **Play** · **Play file** · **Options** · **Exit** (arrows + Enter, or press 1-4).

In the notes console:

```
   w   e       t   y   u       o   p        black keys
 a   s   d   f   g   h   j   k   l   ;   '  white keys (a = C4 … ' = F5)
```

- Press several keys together to play chords; every note runs on its own thread.
- `z` / `x`: octave down / up
- `Esc`: back to the menu

**Options** lets you choose the instrument, octave, note length and volume.

## Note files

**Play file** lists the `*.notes` files in `songs/`. Each line is
`<note(s)> <seconds>`:

```
a4 1.2          # A4 for 1.2 seconds
x 1.2           # rest (silence)
c4 e4 g4 0.8    # several notes = chord
f#4 0.5         # sharps with '#', flats with 'b' (bb3)
```

Notes are `c`-`b` plus an octave number (`a4` = 440 Hz), case-insensitive.
Comments start with a `#` token. Your instrument and volume from **Options**
are used for playback. `Esc` stops playback.

## How it works

```
key ─▶ NOTE_KEY_MAP (notes.py) ─▶ frequency
          └▶ Instrument.voice(freq) ─▶ Voice (partials + envelope)   instruments/
                └▶ NotePlayer.play() ─▶ new thread ─▶ SoxBackend ─▶ `play` process   engine.py
```

Instruments never touch audio. They take a frequency, tweak it into a
`Voice` (a list of partial frequencies, gains and waveforms, plus an envelope
and reverb), and the backend renders that `Voice`. So you can add instruments
without touching the backend, and you can swap the backend without touching
any instrument.

- **piano**: 6 stretched (inharmonic) overtones, a detuned unison string, fast attack, long decay
- **guitar**: Karplus-Strong plucked strings (sox `pluck`), a detuned second string, body resonance

### Adding an instrument

Drop a module into `note_player/instruments/`. It is discovered automatically:

```python
from .base import Instrument, Partial, Voice

class Organ(Instrument):
    name = "organ"
    description = "Drawbar organ"

    def voice(self, frequency, duration):
        return Voice(
            partials=tuple(Partial(frequency * n, gain=1 / n) for n in (1, 2, 3, 4)),
            duration=duration,
            attack=0.02,
            release=0.1,
        )
```

## Tests

```sh
python3 -m unittest -v
```
# cli_music_player
