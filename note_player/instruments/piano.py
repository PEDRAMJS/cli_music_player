"""Piano: inharmonic partials with a fast attack and a long, soft decay."""

from __future__ import annotations

import math

from .base import Instrument, Partial, Voice

# Stiff piano strings push upper partials sharp: f_n = n * f * sqrt(1 + B * n^2).
INHARMONICITY = 0.0004
PARTIAL_COUNT = 6
# Each note on a real piano is 2-3 slightly detuned strings; this adds the "shimmer".
UNISON_DETUNE_CENTS = 1.5


class Piano(Instrument):
    name = "piano"
    description = "Hammered strings: bright attack, inharmonic overtones, reverb"

    def voice(self, frequency: float, duration: float) -> Voice:
        partials = []
        for n in range(1, PARTIAL_COUNT + 1):
            freq = n * frequency * math.sqrt(1 + INHARMONICITY * n * n)
            # Higher notes are darker on a piano: their overtones fall off faster.
            rolloff = 1.2 + frequency / 600
            partials.append(Partial(freq, gain=1 / n**rolloff, waveform="sine"))
        detuned = frequency * 2 ** (UNISON_DETUNE_CENTS / 1200)
        partials.append(Partial(detuned, gain=0.35, waveform="sine"))
        return Voice(
            partials=tuple(partials),
            duration=duration,
            attack=0.004,
            release=duration * 0.85,
            reverb=30,
            tail=0.4,
        )
