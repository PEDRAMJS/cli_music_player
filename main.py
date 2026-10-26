#!/usr/bin/env python3
"""Usage: python3 main.py [song.notes]"""
import sys

from note_player.ui import run

if __name__ == "__main__":
    sys.exit(run(sys.argv[1] if len(sys.argv) > 1 else None))
