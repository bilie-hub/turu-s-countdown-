# Every Light Turns Green

A slow, late-night ballad about driving alone through an empty city at 2 AM, after something has ended. It sits in ambient melodic trap / dark dream-pop. The tone is calm resignation, not anger.

| File | What it is |
|---|---|
| `every_light_turns_green_instrumental.mp3` | The full instrumental, mastered to -14 LUFS with a -1 dBTP ceiling |
| `every_light_turns_green_topline_guide.mp3` | The same mix with a synth "whistle" playing the sung melody. **It's a placeholder, not a vocal.** Use it to learn the melody. |
| `render.py` | Builds both files from scratch with numpy/scipy. It uses no samples. Pass `--stems` to export separate WAVs for each instrument group. |

- **Key:** F minor
- **Tempo:** 70 BPM felt (programmed as 140 halftime)
- **Length:** 3:07, which includes about 9 seconds of reverb tail

## Structure

| Time | Section | Chords (one per bar at 70) | What happens |
|---|---|---|---|
| 0:00 | Intro | Dbmaj9 · Eb6/9 · Cm7 · Fm9 | The music box is filtered so it sounds underwater, and slowly comes up. A car passes outside, with tape hiss underneath. No drums. A reversed reverb swell breathes in. |
| 0:13.7 | Verse 1 | Fm9 · Dbmaj9 · Bbm9 · Csus4→C7b9 | The filter opens fully. The 808 enters with long sustained notes. The rim hits on 2 and 4 and the hats start as sparse quarter notes. The music box thins out so the spoken vocal has room. The drums and 808 stop on the last beat. |
| 0:41.1 | Chorus 1 | Dbmaj9 · Eb6/9 · Cm7 · Fm9 | The 808 starts sliding up an octave and back. Hats move to eighth notes with soft 32nd rolls. An octave-up shimmer layer is added, mostly sent into the reverb. The C7 at the end of the verse resolves to Db instead of home. That deceptive cadence is the ache. |
| 1:08.6 | Verse 2 | as Verse 1 | The hats drop out for four bars, so the drums are just 808 and rim, then come back with a triplet roll. |
| 1:36.0 | Chorus 2 | as Chorus | Open hats and more rolls. A ghost rim lands just before each turnaround. |
| 2:03.4 | Bridge | Bbm9 · Dbmaj9 · Gbmaj7#11 · Csus4→C7b9 | The drums drop out. The 808 holds single long notes. The music box plays one long note at a time with heavier reverb. Another car passes. On the last beat everything drops out except the reverb tail and a reversed swell. |
| 2:17.1 | Chorus 3 | as Chorus | Full chorus. It thins out over the last two bars. |
| 2:44.6 | Outro | as Chorus | The drums are gone. The whole bed sinks under a low-pass filter that falls from 20 kHz to about 300 Hz. Then two music-box notes ring out on their own, unfiltered: the root F, then an unresolved G, the 9th. |

## Lyrics and vocal direction

The verses are **spoken**: low, half-rasp, with your mouth a few centimetres from the capsule so the proximity effect does the work. The choruses and bridge lift into **falsetto**. The falsetto peak climbs through the song: "green" lands on C5 in line 1, Eb5 in line 3 and F5 in line 7. Each chorus ends by dropping straight back into the speaking voice. The guide track has no notes in those spoken spots on purpose.

**Verse 1** (0:13.7, one line per bar)
> Two-fourteen. The avenue's a runway, nobody on it
> Your hair tie's on the gear shift — I keep meaning to toss it
> Streetlights crawl across the dash like a slow rewind
> Every one's another month of us, and then it's behind
> Radio keeps playing all the songs you used to skip
> I don't change it anymore. I guess I got used to it
> Took the long way past your building, like I always do
> Didn't slow down this time. Didn't look for you.

**Chorus** (0:41.1 · 1:36.0 · 2:17.1)
> Every light turns green
> Like the city knows I'm leaving
> Every light turns green
> Nothing left to stop me now
> You're getting smaller in the mirror
> Slower than I thought you would
> Every light turns green *(highest note so far, let it strain)*
> *(spoken, back in the chest)* …and it doesn't feel good.

In Chorus 3 the last line becomes: *…and maybe that's good.*

**Verse 2** (1:08.6)
> Passenger seat's still tilted back the way you liked it
> I could fix it in a second. I don't. I just ride with it
> Gas station on the corner glowing like an empty fish tank
> Tried to list the reasons that we ended, kept on drawing blanks
> It's not that I miss you — it's that I miss who I was
> Back when I said "forever" and I meant it just because
> Now the city's just a screensaver I'm driving through
> Every exit's got a memory, and none of them are new

**Bridge** (2:03.4, drums out, all falsetto, fragile)
> I hope somebody's waiting up for you
> I hope they leave the porch light on
> I hope you never have to drive this road
> At two a.m. alone

On "alone", the voice sits on F5 against the C7b9 chord and then falls to E5. That suspension resolving is the emotional peak of the song. If the voice cracks there, keep that take.

**Outro** (about 2:51, whispered, off-mic)
> Green again.

### Topline (matches the guide track)

| Line | Notes |
|---|---|
| Ev-ery light turns green | F4 Ab4 Bb4 Ab4 **C5**~ |
| Like the ci-ty knows I'm leav-ing | Bb4 Ab4 G4 Ab4 Bb4 Ab4 G4 Eb4 |
| Ev-ery light turns green | G4 Ab4 Bb4 C5 **Eb5**~ C5 |
| No-thing left to stop me now | Ab4 G4 F4 Eb4 F4 G4 F4~ |
| You're get-ting small-er in the mir-ror | F4 Ab4 Ab4 C5 Bb4 Ab4 Ab4 Bb4 Ab4 |
| Slow-er than I thought you would | G4 Ab4 Bb4 C5 Bb4 Ab4 G4~ |
| Ev-ery light turns green | Bb4 C5 Eb5 Eb5 **F5**~ Eb5 C5 |
| I hope some-bo-dy's wait-ing up for you | F4 Ab4 Bb4 C5 Bb4 Db5 C5 Bb4 Ab4 F4 |
| I hope they leave the porch light on | F4 Ab4 Bb4 C5 Bb4 Eb5 Db5 C5 |
| I hope you ne-ver have to drive this road | Ab4 Bb4 C5 Db5 C5 Bb4 C5 Db5 Eb5 **F5**~ |
| At two a. m. a-lone | C5 C5 Bb4 C5 Bb4 **F5→E5** |

These pitches are written for a male falsetto. If F5 is out of reach, re-render the whole song lower with `python3 ballad/render.py --transpose -2` (or -3, and so on).

## How the brief maps to the sound

- **Glassy, crystalline top (music box / FM chime).** Each note opens with a bright 1:3 FM attack and then settles into a pure sine, the way a celesta or music box does. A short inharmonic partial at 6.27× the fundamental gives the "tine" sound. Slow tape wow and a few cents of random detune make it sound old. The motif is written as positions within the chord rather than fixed notes, so the same falling figure follows every chord without ever playing a wrong note.
- **Lush, cavernous reverb.** This is a synthetic stereo hall with about a 6 s decay. The low, mid and high bands each decay at their own rate, so the tail gets darker as it dies. It is fed by the chime, a dotted-eighth ping-pong delay and a little of the pad. The amount follows the section: drier in the verses so the spoken vocal stays intimate, and about twice as much in the bridge and outro.
- **Warm, low-filtered, submerged pads.** Detuned saw stacks run through a slowly moving low-pass filter. It sits around 400–900 Hz in the intro and opens to about 1.5 kHz in the chorus. A high-pass at 140 Hz keeps them out of the 808's way.
- **Slow halftime 808 that slides instead of punching.** The attack takes 8 ms, and the pitch drop on each hit is only 15%, so it never thumps. Slides are true legato: the note glides about 50 ms to the new pitch without retriggering. Gentle saturation lets it come through on phone speakers.
- **Spaced-out crisp hats, dry snapping rim.** The hats are metallic square-wave clusters plus noise, high-passed at 7 kHz. The rolls are soft 32nds, never rapid-fire. The rim gets no reverb at all, and the 808 cuts out around it, which leaves pockets of silence.
- **Mids open for a close-mic vocal.** Instruments are panned wide, and from the first verse to the last chorus a mid/side EQ cuts the centre of the music bus by 4.5 dB around 2.3 kHz and 1.5 dB around 450 Hz. Measured in the chorus, 2–4 kHz sits 10–15 dB below 1 kHz. That gap is where the voice goes.
- **A memory fading in real time.** The intro starts filtered underwater, there are reversed swells before the drops, the bridge dims, and the outro sinks under the filter until only one clear note is left.

## Re-rendering

```bash
pip install numpy scipy pyloudnorm   # pyloudnorm is optional, for accurate LUFS
python3 ballad/render.py             # writes both mp3s next to this file
python3 ballad/render.py --stems     # + WAV stems: music_box, pads, reverb, hats, rim, 808, ambience, guide
python3 ballad/render.py --transpose -2   # whole song down a tone, for a lower voice
```

The render is deterministic: the random seed is 214, as in 2:14 AM. The arrangement is set in the `SECTIONS`, `CHORDS` and pattern tables at the top of `render.py`, and the balance between instrument groups is in `MIX`.

## What this is and isn't

This is a synthesized demo: a complete arrangement, harmony and topline, rendered by code. It is not a finished record. A producer taking it to final should:

- swap in a real 808 sample
- swap in a sampled celesta or music box
- record the vocal, which is the song

The lyric details are placeholders that sound specific. If this song is about something real, replace every one of them with your own details. Those details are the only part of this lane (Joji / late-night Weeknd / Juice WRLD) that can't be copied.

---

# Last Light (solo piano)

`last_light_piano.mp3` is a separate, tragic solo-piano piece in D minor at 64 BPM, about 3:17 long. `piano.py` renders it the same way `render.py` builds the song above: no samples, deterministic output.

| Time | Section | What happens |
|---|---|---|
| 0:00 | Intro | Falling two-note sighs over low chords |
| 0:15 | Theme | The melody over a rolling left hand |
| 0:45 | Theme again | Louder, with the melody doubled in octaves |
| 1:16 | Rising | Crescendo; the left hand speeds up to sixteenths, and a scale run throws into the peak |
| 1:46 | Breaking | The climax: high held notes in octaves with chords filling them, octave bass on 1 and 3, peaking on a high F twice |
| 2:17 | Impact | One crashing D-minor chord across the whole keyboard, then silence |
| 2:22 | What's left | The theme an octave higher with almost nothing under it |
| 2:53 | Ending | Slows to a stop and ends on a single low, open D |
