"""Screens: main menu, options, and the live notes console."""

from __future__ import annotations

import sys
import time
from pathlib import Path

from . import instruments, sequencer
from .engine import NotePlayer
from .keyboard import RawKeyboard
from .notes import NOTE_KEY_MAP, frequency_for, note_name
from .settings import Settings

SONGS_DIR = Path(__file__).resolve().parent.parent / "songs"
PROGRESS_WIDTH = 30

CLEAR = "\x1b[2J\x1b[H"
BOLD, DIM, INVERT, RESET = "\x1b[1m", "\x1b[2m", "\x1b[7m", "\x1b[0m"

# A held key auto-repeats in the terminal; repeats arrive every ~30-50 ms.
# Presses of the same key closer together than this are treated as repeats.
REPEAT_WINDOW = 0.09


def _draw(lines: list[str]) -> None:
    sys.stdout.write(CLEAR + "\n".join(lines) + "\n")
    sys.stdout.flush()


def _choose(keyboard: RawKeyboard, title: str, options: list[str], footer: str = "") -> int | None:
    """Arrow-key / number menu. Returns the selected index, or None on Esc."""
    selected = 0
    while True:
        lines = [f"{BOLD}{title}{RESET}", ""]
        for i, label in enumerate(options):
            marker = f"{INVERT} {i + 1}. {label} {RESET}" if i == selected else f" {i + 1}. {label}"
            lines.append("  " + marker)
        lines += ["", f"{DIM}↑/↓ move · Enter select · Esc back{RESET}"]
        if footer:
            lines.append(footer)
        _draw(lines)

        key = keyboard.read_key()
        if key in ("up", "w", "k"):
            selected = (selected - 1) % len(options)
        elif key in ("down", "s", "j"):
            selected = (selected + 1) % len(options)
        elif key == "enter":
            return selected
        elif key == "esc":
            return None
        elif key and key.isdigit() and 1 <= int(key) <= len(options):
            return int(key) - 1


def options_screen(keyboard: RawKeyboard, settings: Settings) -> None:
    names = instruments.available()
    selected = 0
    rows = 5
    while True:
        values = [
            f"Instrument   ◀ {settings.instrument:<8} ▶",
            f"Octave       ◀ {settings.octave_shift:+d}{'':<6} ▶",
            f"Duration     ◀ {settings.duration:.2f}s{'':<3} ▶",
            f"Volume       ◀ {settings.volume:>3}%{'':<4} ▶",
            "Back",
        ]
        lines = [f"{BOLD}Options{RESET}", ""]
        for i, value in enumerate(values):
            lines.append("  " + (f"{INVERT} {value} {RESET}" if i == selected else f" {value}"))
        description = instruments.create(settings.instrument).description
        lines += ["", f"{DIM}{settings.instrument}: {description}{RESET}"]
        lines += ["", f"{DIM}↑/↓ move · ←/→ change · Esc back{RESET}"]
        _draw(lines)

        key = keyboard.read_key()
        if key == "up":
            selected = (selected - 1) % rows
        elif key == "down":
            selected = (selected + 1) % rows
        elif key == "esc" or (key == "enter" and selected == rows - 1):
            return
        elif key in ("left", "right"):
            step = 1 if key == "right" else -1
            if selected == 0:
                index = names.index(settings.instrument) if settings.instrument in names else 0
                settings.instrument = names[(index + step) % len(names)]
            elif selected == 1:
                settings.shift_octave(step)
            elif selected == 2:
                settings.change_duration(step)
            elif selected == 3:
                settings.change_volume(step)


def _keyboard_diagram() -> list[str]:
    black = "   w   e       t   y   u       o   p"
    white = " a   s   d   f   g   h   j   k   l   ;   '"
    return [f"  {DIM}{black}{RESET}", f"  {white}"]


def play_console(keyboard: RawKeyboard, settings: Settings, player: NotePlayer) -> None:
    instrument = instruments.create(settings.instrument)
    last_seen: dict[str, float] = {}
    recent: list[str] = []

    def render(status: str = "") -> None:
        lines = [
            f"{BOLD}Notes console{RESET}  ·  {settings.instrument}  ·  octave {settings.octave_shift:+d}"
            f"  ·  vol {settings.volume}%",
            "",
            *_keyboard_diagram(),
            "",
            f"{DIM}z/x octave down/up · Esc back to menu{RESET}",
            "",
            "Played: " + " ".join(recent[-16:]),
        ]
        if status:
            lines += ["", status]
        _draw(lines)

    render()
    while True:
        key = keyboard.read_key()
        if key == "esc":
            player.stop_all()
            return
        if key in ("z", "x"):
            settings.shift_octave(1 if key == "x" else -1)
            render()
            continue
        if key is None or key.lower() not in NOTE_KEY_MAP:
            continue

        now = time.monotonic()
        previous = last_seen.get(key)
        last_seen[key] = now
        if previous is not None and now - previous < REPEAT_WINDOW:
            continue  # auto-repeat from a held key

        frequency = frequency_for(key, settings.octave_shift)
        player.play(instrument, frequency, settings.duration, settings.volume / 100)
        recent.append(note_name(frequency))
        render()


def file_menu(keyboard: RawKeyboard, settings: Settings, player: NotePlayer) -> None:
    files = sorted(SONGS_DIR.glob("*.notes"))
    if not files:
        _draw([f"No .notes files in {SONGS_DIR}", "", f"{DIM}Press any key{RESET}"])
        keyboard.read_key()
        return
    choice = _choose(keyboard, "Play file", [path.stem for path in files])
    if choice is not None:
        play_file(keyboard, settings, player, files[choice])


def play_file(keyboard: RawKeyboard, settings: Settings, player: NotePlayer, path: Path) -> None:
    title = f"{BOLD}♪ {path.name}{RESET}  ·  {settings.instrument}  ·  vol {settings.volume}%"
    try:
        steps = sequencer.load(path)
    except (OSError, sequencer.NoteFileError) as error:
        _draw([title, "", f"Can't play this file: {error}", "", f"{DIM}Press any key{RESET}"])
        keyboard.read_key()
        return

    instrument = instruments.create(settings.instrument)

    def play_note(frequency: float, duration: float) -> None:
        player.play(instrument, frequency, duration, settings.volume / 100)

    def wait(seconds: float) -> bool:
        end = time.monotonic() + seconds
        while (left := end - time.monotonic()) > 0:
            if keyboard.read_key(timeout=left) == "esc":
                return False
        return True

    def show(index: int, step: sequencer.Step) -> None:
        notes = " ".join(note_name(f) for f in step.frequencies) or "rest"
        done = round(PROGRESS_WIDTH * (index + 1) / len(steps))
        _draw([
            title,
            "",
            f"  {notes:<16} {step.duration:g}s",
            "",
            f"  [{'#' * done}{'.' * (PROGRESS_WIDTH - done)}] {index + 1}/{len(steps)}",
            "",
            f"{DIM}Esc stop{RESET}",
        ])

    if sequencer.play(steps, play_note, wait, show):
        _draw([title, "", "  Finished.", "", f"{DIM}Press any key{RESET}"])
        keyboard.read_key()
    else:
        player.stop_all()


def run(song: str | None = None) -> int:
    player = NotePlayer()
    if not player.backend.available():
        print("sox's `play` command was not found. Install sox (e.g. `sudo apt install sox`).")
        return 1
    if not sys.stdin.isatty():
        print("note_player needs an interactive terminal.")
        return 1

    settings = Settings()
    try:
        with RawKeyboard() as keyboard:
            if song:
                play_file(keyboard, settings, player, Path(song))
                return 0
            while True:
                choice = _choose(keyboard, "♪ Note Player", ["Play", "Play file", "Options", "Exit"])
                if choice == 0:
                    play_console(keyboard, settings, player)
                elif choice == 1:
                    file_menu(keyboard, settings, player)
                elif choice == 2:
                    options_screen(keyboard, settings)
                else:
                    break
    except KeyboardInterrupt:
        pass
    finally:
        player.close()
        sys.stdout.write(CLEAR)
        sys.stdout.flush()
    return 0
