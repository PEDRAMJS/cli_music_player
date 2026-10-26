"""Guitar: plucked-string synthesis (Karplus-Strong) with a body resonance."""

from __future__ import annotations

from .base import Instrument, Partial, Voice

# A second, slightly sharp string gives the chorus of steel strings.
STRING_DETUNE_CENTS = 3.0


class Guitar(Instrument):
    name = "guitar"
    description = "Plucked steel string: natural decay, slight chorus"

    def voice(self, frequency: float, duration: float) -> Voice:
        detuned = frequency * 2 ** (STRING_DETUNE_CENTS / 1200)
        return Voice(
            partials=(
                Partial(frequency, gain=1.0, waveform="pluck"),
                Partial(detuned, gain=0.35, waveform="pluck"),
                # A quiet sine an octave down stands in for the hollow body.
                Partial(frequency / 2, gain=0.08, waveform="sine"),
            ),
            duration=duration,
            attack=0.002,
            release=min(0.4, duration / 2),
            reverb=15,
            tail=0.2,
        )
