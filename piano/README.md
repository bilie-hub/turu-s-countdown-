# Piano part from `preview.wav`

The piano part from the 27-second preview, written out so you can play it.

**Key** A minor · **Tempo** 140 BPM · **Time** 4/4 · **Form** one 8-bar loop, heard twice · the piano comes in **1.7 s** into the preview.

![Sheet music](piano-part.png)

| File | Use it for |
|---|---|
| `piano-part.pdf` / `piano-part.png` | Sheet music (two staves) |
| `piano-part.mid` | Any piano-learning app, GarageBand or MuseScore. Two tracks: right hand, left hand. |
| `piano-part.musicxml` | Editable score for MuseScore, Flat or Noteflight |
| `hook-trainer.html` | Open in a browser: falling notes over a keyboard, slow it down, loop one phrase, mute a hand |

## The keys

**Right hand** stays in one place. Put your thumb on the **A just above middle C (A4)**.
Notes used: A4, B4, C5, D5, **D♯5** (the black key between D and E), E5, and one high A5 in bar 13.

**Left hand** plays octaves on **G♯**, **G** and **A** (G♯2 + G♯3, G2 + G3, A2 + A3).

The idea to remember: one figure, **E → D♯ → D**, sliding down a half step at a time, keeps coming back. The bass slides too: **G♯ → G → A**.

Fingering: hook **D♯ E D♯ D** = 4 5 4 3. Answer **A · C · B** = 1 3 2.

## Bar by bar

Count 1 2 3 4 in every bar. ⌒ means keep holding. "3-and" is halfway between beats 3 and 4.

| Bar | Chord | Right hand (beats 1 · 2 · 3 · 4) | Left hand |
|---|---|---|---|
| | | *First pass of the loop: 0:01.7 to 0:15.4 in the preview* | |
| 1 | G♯ | **D♯ · E · D♯ · D**⌒, holding A + C underneath | G♯ octave |
| 2 | G♯ | D⌒ held · **A** on 2 | G♯ octave |
| 3 | G | **D · E · D♯ · D**⌒, holding A underneath | G octave |
| 4 | G | D⌒ · **A** on 2 · **C** on 3-and · **B**⌒ on 4 | G octave |
| 5 | Am | B ends on 1 · rest | A octave |
| 6 | Am | rest | A octave |
| 7 | Am | rest · **E · D♯ · D**⌒ | A octave |
| 8 | Am | D⌒ held | A octave |
| | | *Second pass: 0:15.4 to 0:27.4* | |
| 9 | G♯ | rest · rest · **D♯ · D**⌒ | G♯ octave |
| 10 | G♯ | D⌒ held · **A** on 2 | G♯ octave |
| 11 | G | **D · E · D♯ · D**⌒, holding A underneath | G octave |
| 12 | G | D⌒ · **A** on 2 · **C** on 3-and · **B** on 4 | G octave |
| 13 | Am | high **A** on every beat, with A-D, E, E, A+E under it (rough) | A octave |
| 14 | Am | rest · rest · rest · **E** | A octave |
| 15 | Am | rest · **E · D♯ · D**⌒, A under the E | A octave |
| 16 | Am | D⌒ held (inferred, the preview ends after bar 15) | A octave |

To play along with the preview, start bar 1 at **0:01.7**.

## How it was made, and how far to trust it

- The piano was separated from the full mix (Spleeter, 5 stems), transcribed with a piano model (Transkun) and a general one (Basic Pitch), then snapped to a 140 BPM grid fitted to the audio. Note onsets land within about 10 ms of that grid.
- Every note was checked against the isolated piano audio. Each one is the loudest pitch within two semitones at its moment, so no note is a half step off.
- **Solid:** the hook notes and rhythm, the A · C · B answer, the bass notes, tempo and key.
- **Close:** the held inner notes (A, C) and exactly how long notes ring. Reverb blurs where notes end.
- **Rough:** the bar 13 fill. Bar 16 is copied from bar 8.
- **Arranged:** the left hand. On the record the low end is an 808 bass. The pad chords, the plucked arpeggio in bars 5 to 8, the vocal snippet near 0:24 and the drums are left out on purpose.
- Only the 27-second preview was available. Anything outside it (intro, verses, later changes) is not covered.

This replaces the earlier `preview-transcription.mid`, which was raw model output from the full mix (about 340 notes, including drums and vocals) and was not playable.
