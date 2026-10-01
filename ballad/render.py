#!/usr/bin/env python3
"""
Every Light Turns Green - procedural render.

Synthesizes the instrumental bed for the ballad described in ballad/README.md
entirely from scratch (numpy/scipy, no samples, no presets), plus an optional
topline guide that plays the sung melody so a vocalist can learn it.

    pip install numpy scipy            # pyloudnorm optional (accurate LUFS)
    python3 ballad/render.py           # instrumental + guide mp3
    python3 ballad/render.py --stems   # also write per-bus 24-bit WAV stems
    python3 ballad/render.py --wav     # also write full-mix 24-bit WAVs

Requires ffmpeg on PATH for encoding.
"""

import argparse
import os
import shutil
import subprocess
from functools import lru_cache

import numpy as np
from scipy import signal
from scipy.ndimage import maximum_filter1d, minimum_filter1d, uniform_filter1d

SR = 44100
BPM = 70.0                      # felt tempo; the hats/808 read as 140 halftime
BEAT = 60.0 / BPM
BAR = 4 * BEAT
SIXTEENTH = BEAT / 4
SEED = 214                      # 2:14 AM
TITLE = "Every Light Turns Green"
TRANSPOSE = 0                   # semitones, set by --transpose


def m2f(m):
    return 440.0 * 2.0 ** ((np.asarray(m, dtype=float) + TRANSPOSE - 69.0) / 12.0)


def db(x):
    return 10.0 ** (x / 20.0)


def rng_for(name):
    """Independent, stable random stream per instrument."""
    return np.random.default_rng([SEED, sum(map(ord, name))])


# ---------------------------------------------------------------- harmony ---
# F minor. name: (808 root, warm pad voicing, music-box voicing low->high)
CHORDS = {
    "Fm9":       (29, [53, 56, 60, 63, 67], [77, 80, 84, 87, 91]),
    "Dbmaj9":    (37, [49, 56, 60, 63, 65], [77, 80, 84, 85, 89]),
    "Bbm9":      (34, [53, 58, 60, 61, 65], [77, 80, 82, 84, 85]),
    "Csus4":     (36, [53, 55, 60, 65, 67], [77, 79, 84, 89, 91]),
    "C7b9":      (36, [52, 55, 58, 61, 64], [76, 79, 82, 85, 88]),
    "Eb6/9":     (39, [51, 55, 58, 60, 65], [79, 82, 84, 87, 89]),
    "Cm7":       (36, [48, 55, 58, 63, 67], [79, 82, 84, 87, 91]),
    "Gbmaj7#11": (30, [54, 58, 60, 61, 65], [77, 82, 84, 85, 90]),
}

# VI - VII - v - i : never lands home until the bar it has to.
CHORUS_PROG = ["Dbmaj9", "Eb6/9", "Cm7", "Fm9"]
VERSE_PROG = ["Fm9", "Dbmaj9", "Bbm9", ("Csus4", "C7b9")]
BRIDGE_PROG = ["Bbm9", "Dbmaj9", "Gbmaj7#11", ("Csus4", "C7b9")]

# ------------------------------------------------------------ arrangement ---
CHORUS_HATS = ["eighth", "eighth_open", "eighth", "eighth_roll"] * 2
SECTIONS = [
    dict(name="Intro", bars=4, prog=CHORUS_PROG, chime="full", pad=0.85,
         pad_cut=(420, 900), pocket=0.0, amb=1.0, verb=1.5),
    dict(name="Verse 1", bars=8, prog=VERSE_PROG, chime="sparse", pad=0.75,
         pad_cut=(850, 950), pocket=1.0, amb=0.35, verb=0.8, rim=True, stop=True,
         hats=["quarter"] * 3 + ["quarter_roll", "eighth", "eighth", "eighth_roll", "eighth"],
         bass=["sustain"] * 4 + ["verse"] * 4),
    dict(name="Chorus 1", bars=8, prog=CHORUS_PROG, chime="full", shimmer=True, pad=1.0,
         pad_cut=(1200, 1400), pocket=1.0, amb=0.25, rim=True,
         hats=CHORUS_HATS, bass=["chorus"] * 8, vocal="chorus"),
    dict(name="Verse 2", bars=8, prog=VERSE_PROG, chime="sparse", pad=0.75,
         pad_cut=(850, 950), pocket=1.0, amb=0.35, verb=0.8, rim=True, stop=True,
         hats=[None] * 4 + ["eighth", "eighth", "triplet_roll", "eighth"],
         bass=["verse"] * 8),
    dict(name="Chorus 2", bars=8, prog=CHORUS_PROG, chime="full", shimmer=True, pad=1.0,
         pad_cut=(1250, 1500), pocket=1.0, amb=0.25, rim=True, ghost=True,
         hats=["eighth", "eighth_open", "eighth", "eighth_roll",
               "eighth", "eighth_open", "eighth_roll", "triplet_roll"],
         bass=["chorus"] * 8, vocal="chorus"),
    dict(name="Bridge", bars=4, prog=BRIDGE_PROG, chime="long", pad=1.1,
         pad_cut=(650, 1000), pocket=1.0, amb=1.0, stop=True, pad_stop=True,
         bass=["sustain"] * 3 + ["half"], bass_lvl=0.75, verb=1.6, vocal="bridge"),
    dict(name="Chorus 3", bars=8, prog=CHORUS_PROG, chime="full", shimmer=True, pad=1.05,
         pad_cut=(1300, 1500), pocket=1.0, amb=0.25, rim=True, ghost=True,
         hats=CHORUS_HATS[:6] + ["quarter", None],
         bass=["chorus"] * 6 + ["verse", "sustain"], vocal="chorus"),
    dict(name="Outro", bars=4, prog=CHORUS_PROG, chime="outro", pad=0.75,
         pad_cut=(900, 260), pocket=0.3, amb=1.0, bass=["sustain", None, None, None],
         bass_lvl=0.6, verb=1.5),
]

# Bus gains (linear) going into the master.
MIX = dict(music_box=1.1, pads=0.62, reverb=0.28, hats=0.70, rim=1.0, guide=0.64,
           ambience=1.0, **{"808": 0.9})

# Music-box motif: (beat, index into chime voicing, velocity). Index-based so
# the same contour follows every chord without ever hitting a wrong note.
FULL = [(0.0, 4, 1.0), (0.75, 2, .62), (1.5, 3, .78), (2.0, 1, .55),
        (2.5, 2, .66), (3.0, 0, .50), (3.5, 1, .45)]
FULL_B = [(0.0, 4, .95), (0.75, 3, .60), (1.5, 1, .55), (2.5, 2, .50)]
SPARSE = [(0.0, 4, .80), (1.5, 2, .50), (3.0, 3, .45)]
SPARSE_B = [(0.0, 3, .75), (2.0, 1, .45)]
LONG = [(0.0, 4, .85), (2.0, 2, .55)]
OUTRO_END = [(0.0, 0, .70), (2.0, 4, .30)]   # root, then an unresolved 9th

# 808: (beat, semitones above chord root, length in beats, glide-from-previous)
BASS_PATTERNS = {
    "sustain": [(0.0, 0, 3.85, False)],
    "half": [(0.0, 0, 2.9, False)],
    "verse": [(0.0, 0, 2.4, False), (2.75, 0, 0.75, False), (3.5, 12, 0.45, True)],
    "chorus": [(0.0, 0, 1.4, False), (1.75, 0, 0.75, False),
               (2.5, 12, 0.5, True), (3.0, 0, 0.85, True)],
}


def hat_pattern(kind):
    """(position in 16ths, velocity, open?)"""
    eighths = [(p, .85 if p % 4 == 0 else .55, False) for p in range(0, 16, 2)]
    quarters = [(p, .9 if p == 0 else .72, False) for p in (0, 4, 8, 12)]
    roll32 = [(13 + 0.5 * k, .35 + .07 * k, False) for k in range(6)]
    trip = [(12 + 2 / 3 * k, .4 + .07 * k, False) for k in range(6)]
    return {
        "quarter": quarters,
        "quarter_roll": quarters[:3] + [(12, .8, False)] + roll32,
        "eighth": eighths,
        "eighth_open": eighths[:7] + [(14, .6, True)],
        "eighth_roll": eighths[:6] + [(12, .8, False)] + roll32,
        "triplet_roll": eighths[:6] + trip,
    }[kind]


# Sung melody (topline guide). One list per bar: (beat, midi, length in beats).
# Verses and the last chorus line are spoken, so they are not in the guide.
CHORUS_MELODY = [
    [(0, 65, .5), (.5, 68, .5), (1, 70, .5), (1.5, 68, .5), (2, 72, 1.75)],
    [(.5, 70, .25), (.75, 68, .25), (1, 67, .5), (1.5, 68, .25), (1.75, 70, .5),
     (2.25, 68, .25), (2.5, 67, .75), (3.25, 63, .5)],
    [(0, 67, .5), (.5, 68, .5), (1, 70, .5), (1.5, 72, .5), (2, 75, 1.0), (3, 72, .75)],
    [(.25, 68, .25), (.5, 67, .25), (.75, 65, .5), (1.25, 63, .25), (1.5, 65, .5),
     (2, 67, .5), (2.5, 65, 1.25)],
    [(0, 65, .25), (.25, 68, .25), (.5, 68, .25), (.75, 72, .75), (1.5, 70, .25),
     (1.75, 68, .25), (2, 68, .25), (2.25, 70, .5), (2.75, 68, .75)],
    [(.25, 67, .5), (.75, 68, .25), (1, 70, .25), (1.25, 72, .25), (1.5, 70, .5),
     (2, 68, .5), (2.5, 67, 1.25)],
    [(0, 70, .5), (.5, 72, .5), (1, 75, .5), (1.5, 75, .5), (2, 77, 1.0),
     (3, 75, .5), (3.5, 72, .5)],
    [],
]
BRIDGE_MELODY = [
    [(0, 65, .25), (.25, 68, .5), (.75, 70, .25), (1, 72, .25), (1.25, 70, .25),
     (1.5, 73, .5), (2, 72, .25), (2.25, 70, .5), (2.75, 68, .25), (3, 65, .75)],
    [(0, 65, .25), (.25, 68, .5), (.75, 70, .25), (1, 72, .5), (1.5, 70, .25),
     (1.75, 75, .75), (2.5, 73, .5), (3, 72, .75)],
    [(0, 68, .25), (.25, 70, .5), (.75, 72, .25), (1, 73, .25), (1.25, 72, .25),
     (1.5, 70, .25), (1.75, 72, .25), (2, 73, .5), (2.5, 75, .25), (2.75, 77, 1.0)],
    [(0, 72, .25), (.25, 72, .5), (.75, 70, .25), (1, 72, .5), (1.5, 70, .5),
     (2, 77, .75), (2.75, 76, 1.25)],
]


def timeline():
    bars, n = [], 0
    for sec in SECTIONS:
        for b in range(sec["bars"]):
            c = sec["prog"][b % len(sec["prog"])]
            chords = [(0.0, c[0]), (2.0, c[1])] if isinstance(c, tuple) else [(0.0, c)]
            bars.append(dict(sec=sec, b=b, bar=n, t=n * BAR, chords=chords,
                             last=b == sec["bars"] - 1))
            n += 1
    return bars


def chord_at(bi, beat):
    name = bi["chords"][0][1]
    for bt, nm in bi["chords"]:
        if beat >= bt:
            name = nm
    return CHORDS[name]


# ------------------------------------------------------------- dsp utils ---
def place(buf, t, sig, gain=1.0, pan=0.0):
    """Mix a mono (panned) or stereo signal into buf starting at time t."""
    i = int(round(t * SR))
    if sig.ndim == 1:
        a = (pan + 1) * np.pi / 4
        sig = np.stack([sig * np.cos(a), sig * np.sin(a)], axis=1) * np.sqrt(2)
    if i < 0:
        sig, i = sig[-i:], 0
    m = min(len(sig), len(buf) - i)
    if m > 0:
        buf[i:i + m] += gain * sig[:m]


@lru_cache(maxsize=None)
def _sos(kind, f, order=2):
    return signal.butter(order, f, btype=kind, fs=SR, output="sos")


def filt(x, kind, f, order=2):
    f = tuple(f) if isinstance(f, (list, tuple)) else float(f)
    return signal.sosfilt(_sos(kind, f, order), x, axis=0)


@lru_cache(maxsize=None)
def _lp_q(cents):
    return signal.butter(2, 20.0 * 2 ** (cents / 1200.0), fs=SR, output="sos")


def tv_lowpass(x, fc, block=512):
    """Time-varying 2-pole lowpass; fc is a per-sample cutoff curve."""
    y = np.empty_like(x)
    zi = np.zeros((1, 2) + x.shape[1:])
    for s in range(0, len(x), block):
        e = min(s + block, len(x))
        c = float(np.clip(fc[(s + e) // 2], 20.0, 20000.0))
        sos = _lp_q(int(round(1200 * np.log2(c / 20.0) / 10)) * 10)  # 10-cent steps
        y[s:e], zi = signal.sosfilt(sos, x[s:e], axis=0, zi=zi)
    return y


def peaking(f0, gain_db, q):
    a = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * f0 / SR
    alpha = np.sin(w0) / (2 * q)
    b = [1 + alpha * a, -2 * np.cos(w0), 1 - alpha * a]
    den = [1 + alpha / a, -2 * np.cos(w0), 1 - alpha / a]
    return signal.tf2sos(b, den)


def shelf(f0, gain_db, s=0.8):
    """RBJ high shelf."""
    a = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * f0 / SR
    alpha = np.sin(w0) / 2 * np.sqrt((a + 1 / a) * (1 / s - 1) + 2)
    cw, sa = np.cos(w0), 2 * np.sqrt(a) * alpha
    b = [a * ((a + 1) + (a - 1) * cw + sa), -2 * a * ((a - 1) + (a + 1) * cw), a * ((a + 1) + (a - 1) * cw - sa)]
    den = [(a + 1) - (a - 1) * cw + sa, 2 * ((a - 1) - (a + 1) * cw), (a + 1) - (a - 1) * cw - sa]
    return signal.tf2sos(b, den)


def onepole(x, tau):
    k = np.exp(-1.0 / (tau * SR))
    return signal.lfilter([1 - k], [1, -k], x, axis=0)


def polyblep_saw(f, n, phase0):
    dt = f / SR
    ph = (phase0 + np.arange(n) * dt) % 1.0
    y = 2.0 * ph - 1.0
    lo = ph < dt
    t = ph[lo] / dt
    y[lo] -= t + t - t * t - 1.0
    hi = ph > 1.0 - dt
    t = (ph[hi] - 1.0) / dt
    y[hi] -= t * t + t + t + 1.0
    return y


def section_curve(bars, n, key, default=0.0, smooth=0.3):
    c = np.full(n, float(default))
    last = default
    for bi in bars:
        i0, i1 = int(bi["t"] * SR), int((bi["t"] + BAR) * SR)
        last = bi["sec"].get(key, default)
        c[i0:i1] = last
    c[int(bars[-1]["t"] * SR + BAR * SR):] = last
    return uniform_filter1d(c, max(1, int(smooth * SR)))


def breakpoints(n, points):
    """Log-interpolated curve through (time, value) breakpoints."""
    ts, vs = zip(*points)
    t = np.arange(n) / SR
    return np.exp(np.interp(t, ts, np.log(vs)))


# --------------------------------------------------------------- sources ---
def chime_note(rng, midi, vel, length=3.5, bright=True):
    """Music box / FM glass: glassy FM attack that settles into a pure tine."""
    n = int(length * SR)
    t = np.arange(n) / SR
    f = float(m2f(midi)) * 2 ** (rng.normal(0, 2.5) / 1200)
    wow = (1 + 0.0022 * np.sin(2 * np.pi * 0.5 * t + rng.uniform(0, 6.283))
           + 0.0006 * np.sin(2 * np.pi * 5.7 * t + rng.uniform(0, 6.283)))
    ph = 2 * np.pi * np.cumsum(f * wow) / SR
    tau = 1.5 * (1047.0 / f) ** 0.6
    if bright:
        idx = 1.6 * vel * np.exp(-t / 0.12) + 0.12
        body = np.sin(ph + idx * np.sin(3.0 * ph))
        tine = 0.28 * np.sin(6.27 * ph + rng.uniform(0, 6.283)) * np.exp(-t / 0.05)
        click = rng.standard_normal(n) * np.exp(-t / 0.0015) * 0.05
    else:
        body = np.sin(ph)
        tine = click = 0.0
    octave = 0.10 * np.sin(2.0 * ph) * np.exp(-t / (tau * 0.4))
    sig = body * np.exp(-t / tau) + tine + octave + click
    env = np.minimum(t / 0.0015, 1.0) * np.minimum((length - t) / 0.3, 1.0)
    return sig * env * vel


def pad_chord(rng, notes, dur, attack=0.9, release=1.8):
    n = int((dur + release) * SR)
    t = np.arange(n) / SR
    env = np.where(t < attack, np.sin(0.5 * np.pi * np.minimum(t / attack, 1)) ** 2, 1.0)
    env = env * np.where(t > dur, np.exp(-(t - dur) / (release / 4)), 1.0)
    out = np.zeros((n, 2))
    for m in notes:
        for cents, pan in ((-9, -0.75), (0, 0.0), (9, 0.75)):
            f = float(m2f(m)) * 2 ** ((cents + rng.normal(0, 1.5)) / 1200)
            place(out, 0, polyblep_saw(f, n, rng.uniform()), pan=pan)
    return out * env[:, None]


HAT_METAL = np.array([205.3, 304.4, 369.6, 522.7, 540.0, 800.0])


def hat(rng, vel, open_=False):
    length = 0.7 if open_ else 0.12
    n = int(length * SR)
    t = np.arange(n) / SR
    metal = sum(signal.square(2 * np.pi * f * rng.uniform(0.997, 1.003) * t + rng.uniform(0, 6.283))
                for f in HAT_METAL) / 6
    sig = filt(0.5 * metal + 0.8 * rng.standard_normal(n), "highpass", 7000, 4)
    sig = signal.sosfilt(peaking(10500, 4, 1.2), sig)
    decay = 0.17 if open_ else 0.018 + 0.012 * vel
    env = np.exp(-t / decay) * np.minimum(t / 0.0005, 1)
    return sig * env * vel


def rim(rng, vel):
    n = int(0.15 * SR)
    t = np.arange(n) / SR
    tone = (0.9 * np.sin(2 * np.pi * 1680 * t) * np.exp(-t / 0.011)
            + 0.6 * np.sin(2 * np.pi * 465 * t) * np.exp(-t / 0.018))
    click = filt(rng.standard_normal(n), "highpass", 2000) * np.exp(-t / 0.002)
    sig = np.tanh(2.5 * (tone + 0.6 * click))
    return filt(sig, "highpass", 250) * vel


def render_808(events, n):
    """Mono 808 line. Notes flagged glide slide from the previous pitch
    without retriggering, so a phrase is one continuous, soft-attack tone."""
    phrases = []
    for ev in sorted(events):
        if ev[3] and phrases:
            phrases[-1].append(ev)
        else:
            phrases.append([ev])
    out = np.zeros(n)
    for ph in phrases:
        t0 = ph[0][0]
        span = ph[-1][0] + ph[-1][2] - t0
        rel = 0.06
        i0 = int(round(t0 * SR))
        m = min(int((span + rel) * SR), n - i0)
        if m <= 0:
            continue
        tt = np.arange(m) / SR
        f_prev = float(m2f(ph[0][1]))
        f = f_prev * (1 + 0.15 * np.exp(-tt / 0.03))          # gentle drop, not a punch
        for tg, midi, _, _ in ph[1:]:
            k = int(round((tg - t0) * SR))
            fn = float(m2f(midi))
            f[k:] = fn + (f_prev - fn) * np.exp(-(tt[k:] - tt[k]) / 0.05)
            f_prev = fn
        phase = 2 * np.pi * np.cumsum(f) / SR
        env = np.minimum(tt / 0.008, 1.0) * np.exp(-tt / 2.6)
        env *= np.clip((span + rel - tt) / rel, 0, 1)
        knock = np.sin(2 * np.pi * np.cumsum(110 * np.exp(-tt / 0.02) + 55) / SR) * np.exp(-tt / 0.02)
        out[i0:i0 + m] += np.sin(phase) * env + 0.12 * knock
    sat = np.tanh(1.8 * out) / np.tanh(1.8)
    return filt(0.75 * sat + 0.25 * out, "lowpass", 380)


def guide_voice(rng, events, n):
    """Breathy falsetto stand-in: near-sine tone, vocal scoop and late vibrato."""
    out = np.zeros(n)
    for t0, midi, dur in events:
        L = dur + 0.25
        m = int(L * SR)
        t = np.arange(m) / SR
        f = float(m2f(midi)) * (1 - 0.02 * np.exp(-t / 0.06))
        f = f * (1 + 0.006 * np.clip((t - 0.25) / 0.3, 0, 1) * np.sin(2 * np.pi * 5.3 * t))
        ph = 2 * np.pi * np.cumsum(f) / SR
        tone = np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph) + 0.05 * np.sin(4 * ph)
        breath = filt(rng.standard_normal(m), "bandpass", (1500, 6000)) * 0.05
        env = np.minimum(t / 0.05, 1.0) * np.where(t > dur, np.exp(-(t - dur) / 0.06), 1.0)
        i0 = int(round(t0 * SR))
        k = min(m, n - i0)
        out[i0:i0 + k] += ((tone + breath) * env)[:k]
    return out


def make_ir(rng, t60, length, predelay):
    """Synthetic stereo hall: band-split noise with frequency-dependent decay,
    darker as it dies, plus a scatter of early reflections."""
    n = int(length * SR)
    t = np.arange(n) / SR
    bands = [("lowpass", 300), ("bandpass", (300, 2000)), ("bandpass", (2000, 6000)), ("highpass", 6000)]
    ir = np.zeros((n, 2))
    for ch in range(2):
        noise = rng.standard_normal(n)
        for (kind, f), T in zip(bands, t60):
            ir[:, ch] += signal.sosfiltfilt(_sos(kind, f, 4), noise) * 10 ** (-3 * t / T)
        for _ in range(12):
            d = rng.uniform(0.006, 0.075)
            ir[int(d * SR), ch] += rng.choice([-1, 1]) * 2.5 * (1 - d / 0.09)
    ir *= (1 - np.exp(-t / 0.03))[:, None]
    ir = np.vstack([np.zeros((int(predelay * SR), 2)), ir])
    return ir / np.sqrt(np.sum(ir ** 2) / 2)


def convolve(send, ir):
    mono = send.mean(axis=1) if send.ndim == 2 else send
    return np.stack([signal.oaconvolve(mono, ir[:, c])[:len(mono)] for c in range(2)], axis=1)


def pingpong(x, delay, fb=0.42, echoes=6, lp=4500):
    mono = x.mean(axis=1)
    out = np.zeros_like(x)
    d = int(delay * SR)
    y = mono
    for k in range(1, echoes + 1):
        y = filt(y, "lowpass", lp, 1) * fb
        if k * d < len(mono):
            out[k * d:, k % 2] += y[:len(mono) - k * d]
    return out


def car_pass(rng, length=7.0):
    """A car going by outside: brown-ish noise through a doppler-ish sweep."""
    n = int(length * SR)
    t = np.arange(n) / SR
    mid = length / 2
    noise = filt(np.cumsum(rng.standard_normal(n)), "highpass", 40)
    noise /= np.std(noise) + 1e-12
    fc = 250 + 1300 * np.exp(-((t - mid) / 0.9) ** 2) + 150 * (t > mid)
    sig = tv_lowpass(noise[:, None], fc)[:, 0]
    sig *= np.exp(-((t - mid) / 1.5) ** 2)
    pan = np.tanh((t - mid) / 1.2) * 0.8
    a = (pan + 1) * np.pi / 4
    return np.stack([sig * np.cos(a), sig * np.sin(a)], axis=1) * np.sqrt(2)


# ----------------------------------------------------------------- render ---
def render(bars, n, with_guide):
    R = {k: rng_for(k) for k in ("chime", "pad", "drums", "amb", "ir", "guide", "swell")}
    hall = make_ir(R["ir"], t60=(4.5, 6.0, 4.0, 2.4), length=8.0, predelay=0.035)
    plate = make_ir(R["ir"], t60=(1.4, 1.9, 1.5, 0.9), length=2.6, predelay=0.02)

    # music box
    chime, shimmer, coda = np.zeros((n, 2)), np.zeros((n, 2)), np.zeros((n, 2))
    for bi in bars:
        sec, b = bi["sec"], bi["b"]
        style = sec["chime"]
        pat = {"full": FULL_B if b % 4 == 3 else FULL,
               "sparse": SPARSE_B if b % 4 == 3 else SPARSE,
               "long": LONG,
               "outro": [FULL, FULL, SPARSE, OUTRO_END][min(b, 3)]}[style]
        is_coda = style == "outro" and bi["last"]
        tail = 9.0 if is_coda else 5.0 if style in ("long", "outro") else 3.5
        for beat, idx, vel in pat:
            m = chord_at(bi, beat)[2][idx]
            t = bi["t"] + beat * BEAT + R["chime"].normal(0, 0.004)
            v = float(np.clip(vel + R["chime"].normal(0, 0.05), 0.2, 1.0))
            pan = -0.6 + 0.3 * idx            # wide, so the centre stays free for the voice
            # the last two notes skip the outro's underwater filter: one clear light left on
            place(coda if is_coda else chime, t, chime_note(R["chime"], m, v, tail), pan=pan)
            if sec.get("shimmer"):
                place(shimmer, t, chime_note(R["chime"], m + 12, v * 0.5, 3.0, bright=False), pan=-pan)
    chime, coda = filt(chime, "highpass", 250), filt(coda, "highpass", 250)

    # reverse swells into Verse 1 and the last chorus (the breath before the drop)
    swells = np.zeros((n, 2))
    for bi in bars:
        if bi["b"] == 0 and bi["sec"]["name"] in ("Verse 1", "Chorus 3"):
            notes = chord_at(bi, 0)[2][2:]
            dry = sum(chime_note(R["swell"], m, 0.8, 3.0) for m in notes)
            wet = convolve(dry, hall)[:int(2.6 * SR)][::-1]
            wet *= (np.linspace(0, 1, len(wet)) ** 2)[:, None]
            place(swells, bi["t"] - len(wet) / SR, wet)

    # pads (identical neighbouring chords are held, not retriggered)
    events = []
    for bi in bars:
        sec = bi["sec"]
        for k, (beat, name) in enumerate(bi["chords"]):
            end = bi["chords"][k + 1][0] if k + 1 < len(bi["chords"]) else 4.0
            if sec.get("pad_stop") and bi["last"]:
                end = min(end, 3.0)
            t0, t1 = bi["t"] + beat * BEAT, bi["t"] + end * BEAT
            if events and events[-1][2] == name and abs(events[-1][1] - t0) < 1e-6:
                events[-1][1] = t1
            else:
                events.append([t0, t1, name])
    pad = np.zeros((n, 2))
    for t0, t1, name in events:
        place(pad, t0, pad_chord(R["pad"], CHORDS[name][1], t1 - t0))
    cut = np.zeros(n)
    for bi in bars:
        lo, hi = bi["sec"]["pad_cut"]
        frac0, frac1 = bi["b"] / bi["sec"]["bars"], (bi["b"] + 1) / bi["sec"]["bars"]
        i0, i1 = int(bi["t"] * SR), int((bi["t"] + BAR) * SR)
        cut[i0:i1] = np.exp(np.linspace(np.log(lo) + frac0 * np.log(hi / lo),
                                        np.log(lo) + frac1 * np.log(hi / lo), i1 - i0))
    cut[int((bars[-1]["t"] + BAR) * SR):] = bars[-1]["sec"]["pad_cut"][1]
    cut *= 1 + 0.15 * np.sin(2 * np.pi * 0.07 * np.arange(n) / SR)
    pad = tv_lowpass(pad, cut)
    pad = filt(np.tanh(pad * 0.25), "highpass", 140) * section_curve(bars, n, "pad", 0.0)[:, None]

    # 808
    ev = []
    for bi in bars:
        sec = bi["sec"]
        kind = (sec.get("bass") or [None] * sec["bars"])[bi["b"]]
        if not kind:
            continue
        for beat, semis, dur, glide in BASS_PATTERNS[kind]:
            if sec.get("stop") and bi["last"]:
                if beat >= 2.5:
                    continue
                dur = min(dur, 3.0 - beat)
            ev.append((bi["t"] + beat * BEAT, chord_at(bi, beat)[0] + semis, dur * BEAT, glide))
    bass = render_808(ev, n) * section_curve(bars, n, "bass_lvl", 1.0, smooth=0.05)

    # hats + rim (dry: no reverb send at all)
    hats, rims = np.zeros((n, 2)), np.zeros((n, 2))
    rd = R["drums"]
    for bi in bars:
        sec = bi["sec"]
        stop = sec.get("stop") and bi["last"]
        kind = (sec.get("hats") or [None] * sec["bars"])[bi["b"]]
        for pos, vel, open_ in (hat_pattern(kind) if kind else []):
            if stop and pos >= 12:
                continue
            t = bi["t"] + pos * SIXTEENTH + rd.normal(0, 0.002)
            place(hats, t, hat(rd, vel * rd.uniform(0.9, 1.05), open_), pan=-0.2 if open_ else 0.18)
        if sec.get("rim"):
            hits = [(4, 1.0), (12, 0.95)]
            if sec.get("ghost") and bi["b"] % 4 == 3:
                hits.append((15, 0.3))
            for pos, vel in hits:
                if stop and pos >= 12:
                    continue
                place(rims, bi["t"] + pos * SIXTEENTH + rd.normal(0, 0.0015), rim(rd, vel), pan=0.05)

    # the city outside
    ra = R["amb"]
    hiss = filt(ra.standard_normal((n, 2)), "bandpass", (3000, 12000)) * db(-62)
    hum = filt(filt(np.cumsum(ra.standard_normal(n)), "highpass", 25), "lowpass", 140)
    hum = (hum / (np.std(hum) + 1e-12))[:, None] * db(-44) * section_curve(bars, n, "amb", 0.0, 1.0)[:, None]
    cars = np.zeros((n, 2))
    starts = {s["name"]: next(bi["t"] for bi in bars if bi["sec"] is s) for s in SECTIONS}
    for t in (1.2, starts["Bridge"] + 0.5 * BAR, starts["Outro"] + 1.0 * BAR):
        place(cars, t, car_pass(ra))
    amb = hiss + hum + cars * db(-30)

    # music bus: dry + ping-pong + one shared cavernous hall
    delay = pingpong(chime + 0.5 * shimmer, 0.75 * BEAT)
    verb_amt = section_curve(bars, n, "verb", 1.0, smooth=1.0)[:, None]
    hall_send = (0.9 * chime + 1.6 * shimmer + 0.6 * delay) * verb_amt + 0.35 * pad
    hall_ret = filt(filt(convolve(hall_send, hall), "highpass", 220), "lowpass", 9000)
    music_box = signal.sosfilt(shelf(7000, 4.0), 0.55 * chime + 0.15 * shimmer + 0.28 * delay + 0.5 * swells, axis=0)

    # submerged intro, a dimming bridge, and a memory that fades in the outro
    end = bars[-1]["t"] + BAR
    t_v, t_b, t_c3, t_o = starts["Verse 1"], starts["Bridge"], starts["Chorus 3"], starts["Outro"]
    lpf = breakpoints(n, [(0, 380), (t_v - 0.15, 2600), (t_v, 20000),
                          (t_b, 20000), (t_b + BAR, 2400), (t_c3 - 0.05, 2400), (t_c3, 20000),
                          (t_o, 20000), (end, 320), (n / SR, 200)])
    pocket = section_curve(bars, n, "pocket", 0.0, smooth=0.5)

    def music_bus(x):
        x = tv_lowpass(x, lpf)
        # vocal pocket: carve the centre around 450 Hz and 1.2-4 kHz so the voice sits in front
        mid, side = (x[:, 0] + x[:, 1]) / 2, (x[:, 0] - x[:, 1]) / 2
        carved = signal.sosfilt(peaking(2300, -4.5, 0.6), signal.sosfilt(peaking(450, -1.5, 0.9), mid))
        mid = mid + pocket * (carved - mid)
        return np.stack([mid + side, mid - side], axis=1)

    stems = {
        "music_box": MIX["music_box"] * (music_bus(music_box) + 0.55 * coda),
        "pads": MIX["pads"] * music_bus(pad),
        "reverb": MIX["reverb"] * (music_bus(hall_ret) + 1.4 * filt(convolve(coda, hall), "highpass", 220)),
        "hats": MIX["hats"] * hats,
        "rim": MIX["rim"] * rims,
        "808": MIX["808"] * np.stack([bass, bass], axis=1),
        "ambience": MIX["ambience"] * amb,
    }

    if with_guide:
        gev = []
        for bi in bars:
            which = bi["sec"].get("vocal")
            mel = {"chorus": CHORUS_MELODY, "bridge": BRIDGE_MELODY}.get(which)
            if mel:
                for beat, midi, dur in mel[bi["b"] % len(mel)]:
                    gev.append((bi["t"] + beat * BEAT, midi, dur * BEAT))
        g = guide_voice(R["guide"], gev, n)
        g = np.stack([g, g], axis=1)
        stems["guide"] = MIX["guide"] * (g + 0.3 * convolve(g, plate) + 0.12 * pingpong(g, 0.75 * BEAT, fb=0.3, echoes=3))
    return stems


def loudness(x):
    try:
        import pyloudnorm
        return pyloudnorm.Meter(SR).integrated_loudness(x)
    except ImportError:  # rough K-ish approximation
        k = signal.sosfilt(peaking(2000, 4, 0.7), filt(x, "highpass", 60), axis=0)
        return 10 * np.log10(np.mean(k ** 2) * 2 + 1e-12) - 0.691


def master(mix, target_lufs=-14.0, ceiling_db=-1.0):
    # glue: gentle 2:1 RMS compression on the bus
    lvl = np.sqrt(onepole(np.mean(mix ** 2, axis=1), 0.05)) + 1e-9
    ref = np.percentile(lvl, 95)
    over = np.maximum(20 * np.log10(lvl / ref) + 4, 0)
    mix = mix * db(-onepole(over * 0.5, 0.12))[:, None]
    # tape-ish warmth
    mix = np.tanh(mix / np.max(np.abs(mix)) * 1.2) / np.tanh(1.2)
    # loudness, then a lookahead peak limiter and a true-peak check
    mix *= db(target_lufs - loudness(mix))
    c = db(ceiling_db)
    la = int(0.005 * SR)
    peak = maximum_filter1d(np.max(np.abs(mix), axis=1), 2 * la + 1)
    gain = uniform_filter1d(minimum_filter1d(np.minimum(1.0, c / np.maximum(peak, 1e-9)), 2 * la + 1), la)
    mix *= gain[:, None]
    tp = np.max(np.abs(signal.resample_poly(mix, 4, 1, axis=0)))
    if tp > c:
        mix *= c / tp
    gr = 20 * np.log10(np.min(gain))
    return mix, gr


def encode(x, path, comment):
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-"]
    if path.endswith(".mp3"):
        cmd += ["-c:a", "libmp3lame", "-b:a", "192k", "-metadata", f"title={TITLE}",
                "-metadata", f"comment={comment}"]
    else:
        cmd += ["-c:a", "pcm_s24le"]
    subprocess.run(cmd + [path], input=x.astype(np.float32).tobytes(), check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--stems", action="store_true", help="write per-bus WAV stems")
    ap.add_argument("--wav", action="store_true", help="also write 24-bit WAV masters")
    ap.add_argument("--transpose", type=int, default=0, help="semitones, e.g. -2 for a lower voice")
    args = ap.parse_args()
    global TRANSPOSE
    TRANSPOSE = args.transpose
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg is required on PATH")
    os.makedirs(args.out, exist_ok=True)

    bars = timeline()
    end = bars[-1]["t"] + BAR
    n = int((end + 9.0) * SR)
    print(f"{TITLE}: {len(bars)} bars at {BPM:g} BPM (halftime), {n / SR:.1f}s")
    for s in SECTIONS:
        t = next(bi["t"] for bi in bars if bi["sec"] is s)
        print(f"  {int(t // 60)}:{t % 60:04.1f}  {s['name']}")

    stems = render(bars, n, with_guide=True)
    fade = np.clip((n / SR - np.arange(n) / SR) / 4.0, 0, 1)[:, None]
    slug = "every_light_turns_green" + (f"_{args.transpose:+d}st" if args.transpose else "")
    beat_keys = [k for k in stems if k != "guide"]
    for name, keys, comment in (("instrumental", beat_keys, "Instrumental"),
                                ("topline_guide", beat_keys + ["guide"],
                                 "Instrumental + synth topline guide (not a vocal)")):
        mix, gr = master(sum(stems[k] for k in keys) * fade)
        print(f"  {name}: {loudness(mix):.1f} LUFS, limiter {gr:.1f} dB")
        encode(mix, os.path.join(args.out, f"{slug}_{name}.mp3"), comment)
        if args.wav:
            encode(mix, os.path.join(args.out, f"{slug}_{name}.wav"), comment)
    if args.stems:
        # unmastered, one shared gain so they sum back to the mix with -1 dBFS of headroom
        g = db(-1.0) / np.max(np.abs(sum(stems.values())))
        os.makedirs(os.path.join(args.out, "stems"), exist_ok=True)
        for k, x in stems.items():
            encode(x * fade * g, os.path.join(args.out, "stems", f"{slug}_{k}.wav"), k)


if __name__ == "__main__":
    main()
