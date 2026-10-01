#!/usr/bin/env python3
"""
Last Light - a tragic solo piano piece, synthesized from scratch.

    python3 ballad/piano.py          # writes ballad/last_light_piano.mp3

D minor, 64 BPM, with a ritardando into the ending. The piano is additive:
three slightly detuned strings per note (the beating gives the two-stage
decay), stretched inharmonic partials, velocity-dependent brightness, and a
felt hammer thump, played into a synthetic concert-hall reverb.
"""

import os
import shutil

import numpy as np

from render import SR, convolve, db, encode, filt, make_ir, master

BPM = 64.0
SEED = 1104
NOTE = {n: i for i, n in enumerate(["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"])}


def midi(name):
    pitch, octave = name[:-1], int(name[-1])
    return 12 * (octave + 1) + NOTE[pitch]


# Left hand: low -> high voicing, played as a rolling arpeggio.
CHORDS = {
    "Dm": [38, 45, 50, 53, 57], "C": [36, 43, 48, 52, 55], "Dm/C": [36, 45, 50, 53, 57],
    "Bb": [34, 41, 46, 50, 53], "A": [33, 40, 45, 49, 52], "A7": [33, 40, 43, 49, 52],
    "Asus4": [33, 40, 45, 50, 52], "Gm/Bb": [34, 43, 50, 55, 58], "Gm": [31, 38, 43, 46, 50],
    "Am": [33, 40, 45, 48, 52],
}
ARP = [0, 1, 2, 3, 4, 3, 2, 1]

A_CHORDS = ["Dm", "C", "Bb", "A", "Dm", "Dm/C", "Gm/Bb", "A7"]
A_MEL = [
    [(0, "A4", 1.5), (1.5, "D5", .5), (2, "F5", 1.5), (3.5, "E5", .5)],
    [(0, "E5", 1.5), (1.5, "D5", .5), (2, "C5", 2)],
    [(0, "D5", 1.5), (1.5, "C5", .5), (2, "Bb4", 1), (3, "A4", 1)],
    [(0, "A4", 3), (3, "C#5", 1)],
    [(0, "D5", 1), (1, "F5", 1), (2, "A5", 1.5), (3.5, "G5", .5)],
    [(0, "F5", 1.5), (1.5, "E5", .5), (2, "D5", 1), (3, "C5", 1)],
    [(0, "Bb4", 1.5), (1.5, "D5", .5), (2, "G5", 1.5), (3.5, "F5", .5)],
    [(0, "E5", 2), (2, "C#5", 2)],
]
B_CHORDS = ["Bb", "C", "Am", "Dm", "Gm", "Bb", "Asus4", "A"]
B_MEL = [
    [(0, "F5", 1), (1, "Bb5", 1), (2, "A5", 1), (3, "F5", 1)],
    [(0, "G5", 1.5), (1.5, "E5", .5), (2, "C6", 2)],
    [(0, "C6", 1), (1, "B5", .5), (1.5, "A5", .5), (2, "E5", 2)],
    [(0, "F5", 1), (1, "A5", 1), (2, "D6", 2)],
    [(0, "D6", 1.5), (1.5, "C6", .5), (2, "Bb5", 1), (3, "G5", 1)],
    [(0, "F5", 1), (1, "D6", 1), (2, "C6", 1), (3, "Bb5", 1)],
    [(0, "A5", 1), (1, "D6", 3)],
    [(0, "C#6", 2), (2, "A5", 1), (3, "E5", 1)],
]
END_CHORDS = ["Gm", "A", "Dm", None]
END_MEL = [[(0, "D5", 4)], [(0, "C#5", 4)], [(0, "A4", 2), (2, "F4", 2)], []]

# (name, chords, melody, melody octave shift, melody velocity, LH velocity, LH style, double melody an octave down)
SECTIONS = [
    ("Intro", A_CHORDS[:4], [[], [], [(2, "C5", 2)], [(0, "A4", 4)]], 0, .35, .30, "sparse", False),
    ("Theme", A_CHORDS, A_MEL, 0, .50, .32, "arp", False),
    ("Theme again", A_CHORDS, A_MEL, 0, .62, .38, "arp", True),
    ("Breaking", B_CHORDS, B_MEL, 0, .85, .55, "arp", True),
    ("What's left", A_CHORDS, A_MEL, 12, .34, .22, "sparse", False),
    ("Ending", END_CHORDS, END_MEL, 0, .30, .22, "sparse", False),
]


def piano_note(rng, m, vel, hold):
    """One struck note: 3 detuned strings x stretched partials + hammer felt."""
    f0 = 440.0 * 2 ** ((m - 69) / 12)
    B = 0.00012 * 2 ** ((m - 60) / 24)                 # inharmonicity grows up the keyboard
    t60 = float(np.interp(m, [21, 60, 108], [18, 9, 1.5]))
    length = min(hold + 0.35, t60)
    n = int(length * SR)
    t = np.arange(n, dtype=np.float32) / SR
    out = np.zeros(n, np.float32)
    bright = 0.6 + 1.6 * vel
    n_part = int(min(28, 12000 / f0))
    for k in range(1, n_part + 1):
        fk = k * f0 * np.sqrt(1 + B * k * k)
        if fk > 16000:
            break
        amp = (1.0 / k ** (2.3 - bright * 0.6)) * (1 + 0.5 * np.sin(k * 1.9))  # hammer-position comb
        tau = t60 / 6.9 / (1 + 0.25 * k * k ** 0.5)
        fast = np.exp(-t / (tau * 0.25))
        slow = np.exp(-t / tau)
        part = np.zeros(n, np.float32)
        for cents in (-1.2, 0.0, 1.0):                  # three strings, slightly out of unison
            part += np.sin(2 * np.pi * fk * 2 ** ((cents + rng.normal(0, .3)) / 1200) * t + rng.uniform(0, 6.28))
        out += amp * part * (0.55 * fast + 0.45 * slow)
    thump = filt(rng.standard_normal(n), "lowpass", 300 + 900 * vel) * np.exp(-t / 0.012) * 0.25
    env = np.minimum(t / 0.002, 1) * np.exp(-np.maximum(t - hold, 0) / 0.09)  # damper
    return (out / 3 + thump) * env * vel ** 1.4


def main():
    rng = np.random.default_rng(SEED)
    bars = [(s, i) for s in SECTIONS for i in range(len(s[1]))]
    # tempo map: steady, then a long ritardando through the last section
    beat_len = []
    for s, i in bars:
        slow = 1.0 + (0.12 + 0.12 * i if s[0] == "Ending" else 0.0) + (0.04 if s[0] == "What's left" else 0)
        beat_len.append(60 / BPM * slow)
    starts = np.concatenate([[0], np.cumsum([4 * b for b in beat_len])])
    n = int((starts[-1] + 10) * SR)
    mix = np.zeros(n, np.float32)
    pan_l, pan_r = np.zeros(n, np.float32), np.zeros(n, np.float32)

    def play(t, m, vel, hold):
        sig = piano_note(rng, m, float(np.clip(vel * rng.uniform(.92, 1.06), .05, 1)), hold)
        i = max(0, int((t + rng.normal(0, .006)) * SR))
        k = min(len(sig), n - i)
        p = np.clip((m - 64) / 40, -.6, .6)              # player's-perspective stereo: bass left
        pan_l[i:i + k] += sig[:k] * np.cos((p + 1) * np.pi / 4)
        pan_r[i:i + k] += sig[:k] * np.sin((p + 1) * np.pi / 4)

    for (s, i), t0, bl in zip(bars, starts, beat_len):
        name, chords, mel, shift, mv, lv, style, dbl = s
        ch = chords[i]
        if ch:
            v = CHORDS[ch]
            if style == "arp":
                for k, idx in enumerate(ARP):              # pedal held through the bar
                    play(t0 + k * bl / 2, v[idx], lv * (1.15 if k == 0 else 1), (8 - k) * bl / 2 + .2)
                if dbl:
                    play(t0, v[0] - 12, lv * .9, 4 * bl)   # octave bass for weight
            else:
                play(t0, v[0], lv, 4 * bl)
                play(t0 + 1.5 * bl, v[2], lv * .8, 2.5 * bl)
                play(t0 + 2 * bl, v[3], lv * .7, 2 * bl)
        elif name == "Ending":
            play(t0, midi("D2"), .30, 9.0)                  # the last thing: a low, open D
            play(t0 + .05, midi("D1"), .26, 9.0)
        for beat, note, dur in mel[i]:
            m = midi(note) + shift
            accent = 1.1 if beat == 0 else 1.0
            play(t0 + beat * bl, m, mv * accent, dur * bl + .15)
            if dbl:
                play(t0 + beat * bl + .012, m - 12, mv * .75, dur * bl + .15)

    dry = np.stack([pan_l, pan_r], axis=1).astype(np.float64)
    dry = filt(dry, "highpass", 30)
    hall = make_ir(np.random.default_rng(SEED + 1), t60=(3.2, 3.0, 2.2, 1.4), length=5.0, predelay=0.025)
    wet = filt(convolve(dry, hall), "highpass", 120)
    mix_st = dry + 0.32 * wet
    fade = np.clip((n / SR - np.arange(n) / SR) / 3.0, 0, 1)[:, None]
    out, _ = master(mix_st * fade, target_lufs=-16.0)
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_light_piano.mp3")
    encode(out, path, "Solo piano")
    print(f"{path}: {n / SR:.0f}s")
    for name, t in zip([s[0] for s in SECTIONS], [starts[[b[0] for b in bars].index(s)] for s in SECTIONS]):
        print(f"  {int(t // 60)}:{t % 60:04.1f}  {name}")


if __name__ == "__main__":
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg is required on PATH")
    main()
