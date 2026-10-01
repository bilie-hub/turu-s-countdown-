#!/usr/bin/env python3
"""
Last Light - a tragic solo piano piece, synthesized from scratch.

    python3 ballad/piano.py          # writes ballad/last_light_piano.mp3

D minor, 64 BPM with rubato. Shape: a quiet sighing intro, the theme twice,
a two-stage build (Rising -> Breaking) that crests on a crashing D minor
chord, a bar of silence, then the theme an octave higher with almost
nothing under it, and a ritardando into one low open D.

The piano is additive: three slightly detuned strings per note (the beating
gives the two-stage decay), stretched inharmonic partials, velocity-
dependent brightness, a felt hammer thump, and a fuller, louder bass
register so the low notes carry. It plays into a synthetic hall.
"""

import os
import shutil

import numpy as np

from render import SR, convolve, encode, filt, make_ir, master

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
ARP8 = [0, 1, 2, 3, 4, 3, 2, 1]                        # eighths
ARP16 = [0, 1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1, 2, 3, 4, 5]  # sixteenths, two octaves

A_CHORDS = ["Dm", "C", "Bb", "A", "Dm", "Dm/C", "Gm/Bb", "A7"]
B_CHORDS = ["Bb", "C", "Am", "Dm", "Gm", "Bb", "Asus4", "A"]

# A falling two-note sigh per bar, so the intro has a voice from the first second.
INTRO_MEL = [
    [(0, "F5", 2), (2, "E5", 2)],
    [(0, "E5", 2), (2, "D5", 2)],
    [(0, "D5", 2), (2, "C5", 2)],
    [(0, "C#5", 3), (3, "E5", 1)],
]
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
# Stage one of the build: climbing, ending in a scale run that throws into the peak.
RISE_MEL = [
    [(0, "F5", 1), (1, "Bb5", 1), (2, "A5", 1), (3, "F5", 1)],
    [(0, "G5", 1.5), (1.5, "E5", .5), (2, "C6", 2)],
    [(0, "C6", 1), (1, "B5", .5), (1.5, "A5", .5), (2, "E5", 2)],
    [(0, "F5", 1), (1, "A5", 1), (2, "D6", 2)],
    [(0, "D6", 1.5), (1.5, "C6", .5), (2, "Bb5", 1), (3, "G5", 1)],
    [(0, "F5", 1), (1, "Bb5", 1), (2, "D6", 2)],
    [(0, "A5", 1), (1, "D6", 3)],
    [(0, "C#6", 2), (2, "E5", .5), (2.5, "F5", .5), (3, "G5", .25), (3.25, "A5", .25),
     (3.5, "Bb5", .25), (3.75, "C#6", .25)],
]
# Stage two: the peak. Long held notes high up, in octaves with chord tones under them.
BREAK_MEL = [
    [(0, "D6", 1.5), (1.5, "C6", .5), (2, "Bb5", 1), (3, "F5", 1)],
    [(0, "E6", 1.5), (1.5, "D6", .5), (2, "C6", 2)],
    [(0, "E6", 2), (2, "C6", 1), (3, "A5", 1)],
    [(0, "F6", 3), (3, "E6", 1)],
    [(0, "D6", 2), (2, "Bb5", 1), (3, "G5", 1)],
    [(0, "F6", 2), (2, "D6", 1), (3, "Bb5", 1)],
    [(0, "E6", 1), (1, "D6", 3)],
    [(0, "C#6", 4)],
]
END_CHORDS = ["Gm", "A", "Dm", None]
END_MEL = [[(0, "D5", 4)], [(0, "C#5", 4)], [(0, "A4", 2), (2, "F4", 2)], []]

# lh: left-hand texture, a string or one per bar. mv/lv: velocity ramp (first bar, last bar).
SECTIONS = [
    dict(name="Intro", chords=A_CHORDS[:4], mel=INTRO_MEL, mv=(.62, .64), lv=(.58, .60), lh="sparse"),
    dict(name="Theme", chords=A_CHORDS, mel=A_MEL, mv=(.58, .62), lv=(.42, .44), lh="arp"),
    dict(name="Theme again", chords=A_CHORDS, mel=A_MEL, mv=(.62, .70), lv=(.44, .50), lh="arp",
         octaves=True),
    dict(name="Rising", chords=B_CHORDS, mel=RISE_MEL, mv=(.68, .88), lv=(.50, .72),
         lh=["arp"] * 6 + ["arp16"] * 2, octaves=True, bass=True),
    dict(name="Breaking", chords=B_CHORDS, mel=BREAK_MEL, mv=(.92, 1.0), lv=(.74, .86), lh="arp16",
         octaves=True, bass=True, harmony=True),
    dict(name="Impact", chords=["Dm"], mel=[[]], mv=(1, 1), lv=(1, 1), lh="impact"),
    dict(name="What's left", chords=A_CHORDS, mel=A_MEL, shift=12, mv=(.60, .56), lv=(.46, .42),
         lh="sparse"),
    dict(name="Ending", chords=END_CHORDS, mel=END_MEL, mv=(.58, .50), lv=(.46, .44), lh="sparse"),
]


def tempo(sec, i):
    """Beat length for bar i of a section: phrase-end breaths and ritardandos."""
    name, last = sec["name"], i == len(sec["chords"]) - 1
    slow = 1.0 + (0.035 if i % 4 == 3 else 0.0)
    if name == "Breaking" and last:
        slow += 0.10
    if name == "Impact":
        slow = 1.35                                    # the held breath after the crash
    if name == "What's left":
        slow += 0.05
    if name == "Ending":
        slow += 0.12 + 0.12 * i
    return 60 / BPM * slow


def piano_note(rng, m, vel, hold):
    """One struck note: 3 detuned strings x stretched partials + hammer felt."""
    f0 = 440.0 * 2 ** ((m - 69) / 12)
    B = 0.00012 * 2 ** ((m - 60) / 24)                 # inharmonicity grows up the keyboard
    t60 = float(np.interp(m, [21, 60, 108], [18, 9, 1.5]))
    length = min(hold + 0.35, t60)
    n = int(length * SR)
    t = np.arange(n, dtype=np.float32) / SR
    out = np.zeros(n, np.float32)
    low = float(np.clip((57 - m) / 24, 0, 1))          # 0 above A3, 1 at A1 and below
    bright = 0.6 + 1.6 * vel
    rolloff = 2.3 - bright * 0.6 - 0.55 * low          # bass strings are rich in upper partials
    n_part = int(min(28 + 12 * low, 12000 / f0))
    for k in range(1, n_part + 1):
        fk = k * f0 * np.sqrt(1 + B * k * k)
        if fk > 16000:
            break
        amp = (1.0 / k ** rolloff) * (1 + 0.5 * np.sin(k * 1.9))  # hammer-position comb
        if k == 1:
            amp *= 1 - 0.35 * low                       # real bass notes are heard mostly via harmonics
        tau = t60 / 6.9 / (1 + 0.25 * k * k ** 0.5)
        fast = np.exp(-t / (tau * 0.25))
        slow = np.exp(-t / tau)
        part = np.zeros(n, np.float32)
        for cents in (-1.2, 0.0, 1.0):                  # three strings, slightly out of unison
            part += np.sin(2 * np.pi * fk * 2 ** ((cents + rng.normal(0, .3)) / 1200) * t + rng.uniform(0, 6.28))
        out += amp * part * (0.55 * fast + 0.45 * slow)
    thump = filt(rng.standard_normal(n), "lowpass", 300 + 900 * vel) * np.exp(-t / 0.012) * 0.25
    env = np.minimum(t / 0.002, 1) * np.exp(-np.maximum(t - hold, 0) / 0.09)  # damper
    return (out / 3 + thump) * env * vel ** 1.2 * (1 + 0.8 * low)


def harmony_note(chord, m):
    """Highest chord tone a third to a sixth below the melody note."""
    pcs = {p % 12 for p in CHORDS[chord]}
    for c in range(m - 3, m - 10, -1):
        if c % 12 in pcs:
            return c
    return None


def main():
    rng = np.random.default_rng(SEED)
    bars = [(s, i) for s in SECTIONS for i in range(len(s["chords"]))]
    beat_len = [tempo(s, i) for s, i in bars]
    starts = np.concatenate([[0], np.cumsum([4 * b for b in beat_len])])
    n = int((starts[-2] + 9.5) * SR)
    pan_l, pan_r = np.zeros(n, np.float32), np.zeros(n, np.float32)

    def play(t, m, vel, hold):
        sig = piano_note(rng, m, float(np.clip(vel * rng.uniform(.93, 1.05), .05, 1)), hold)
        i = max(0, int((t + rng.normal(0, .006)) * SR))
        k = min(len(sig), n - i)
        p = np.clip((m - 64) / 40, -.6, .6)              # player's-perspective stereo: bass left
        pan_l[i:i + k] += sig[:k] * np.cos((p + 1) * np.pi / 4)
        pan_r[i:i + k] += sig[:k] * np.sin((p + 1) * np.pi / 4)

    for (s, i), t0, bl in zip(bars, starts, beat_len):
        count = len(s["chords"])
        frac = i / max(count - 1, 1)
        mv = s["mv"][0] + frac * (s["mv"][1] - s["mv"][0])
        lv = s["lv"][0] + frac * (s["lv"][1] - s["lv"][0])
        lh = s["lh"] if isinstance(s["lh"], str) else s["lh"][i]
        ch = s["chords"][i]

        if lh == "impact":                              # both hands crash on D minor, then let go
            for m, v in ((26, .95), (38, 1.0), (45, .9), (50, .9)):
                play(t0, m, v, 1.6 * bl)
            for m, v in ((62, .85), (65, .9), (69, .9), (74, 1.0), (77, .95), (81, .95), (86, 1.0)):
                play(t0 + .015, m, v, 1.6 * bl)
        elif ch:
            v = CHORDS[ch]
            if lh == "arp":                             # pedal held through the bar
                for k, idx in enumerate(ARP8):
                    play(t0 + k * bl / 2, v[idx], lv * (1.15 if k == 0 else 1), (8 - k) * bl / 2 + .2)
            elif lh == "arp16":
                ext = v + [v[2] + 12, v[3] + 12]
                for k, idx in enumerate(ARP16):
                    acc = 1.15 if k % 4 == 0 else .9
                    play(t0 + k * bl / 4, ext[idx], lv * acc, (16 - k) * bl / 4 + .2)
            else:
                play(t0, v[0], lv * 1.1, 4 * bl)
                play(t0 + bl, v[2], lv * .8, 3 * bl)
                play(t0 + 2 * bl, v[3], lv * .75, 2 * bl)
                play(t0 + 3 * bl, v[4], lv * .7, bl + .3)
            if s.get("bass"):                            # octave bass on 1 (and 3 at the peak)
                play(t0, v[0] - 12, lv, 4 * bl)
                if s.get("harmony"):
                    play(t0 + 2 * bl, v[0] - 12, lv * .85, 2 * bl)
        elif s["name"] == "Ending":
            play(t0, midi("D2"), .52, 8.0)              # the last thing: a low, open D
            play(t0 + .05, midi("D1"), .48, 8.0)

        for beat, note, dur in s["mel"][i]:
            m = midi(note) + s.get("shift", 0)
            vel = mv * (1.1 if beat in (0, 2) else 1.0)
            hold = dur * bl + .15
            play(t0 + beat * bl, m, vel, hold)
            if s.get("octaves"):
                play(t0 + beat * bl + .012, m - 12, vel * .78, hold)
            if s.get("harmony") and beat in (0, 2) and dur >= 1:
                h = harmony_note(ch, m)              # fills the octave with a chord tone
                if h:
                    play(t0 + beat * bl + .02, h, vel * .65, hold)

    dry = np.stack([pan_l, pan_r], axis=1).astype(np.float64)
    dry = filt(dry, "highpass", 30)
    hall = make_ir(np.random.default_rng(SEED + 1), t60=(3.2, 3.0, 2.2, 1.4), length=5.0, predelay=0.025)
    wet = filt(convolve(dry, hall), "highpass", 120)
    mix = dry + 0.32 * wet
    fade = np.clip((n / SR - np.arange(n) / SR) / 3.0, 0, 1)[:, None]
    out, _ = master(mix * fade, target_lufs=-15.0)
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_light_piano.mp3")
    encode(out, path, "Solo piano")
    print(f"{path}: {n / SR:.0f}s")
    for s in SECTIONS:
        t = starts[next(k for k, (b, _) in enumerate(bars) if b is s)]
        print(f"  {int(t // 60)}:{t % 60:04.1f}  {s['name']}")


if __name__ == "__main__":
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg is required on PATH")
    main()
