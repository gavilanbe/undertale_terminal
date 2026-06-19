#!/usr/bin/env python3
"""Generate all WAV sound assets (no external deps, uses stdlib wave+struct)."""

import wave
import struct
import math
import os
import random

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
SR = 22050  # sample rate


def _write(filename, samples):
    path = os.path.join(ASSETS_DIR, filename)
    with wave.open(path, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        for s in samples:
            v = int(max(-32767, min(32767, s)))
            f.writeframes(struct.pack('<h', v))
    print(f"  [OK] {filename} ({len(samples)} samples, {len(samples)/SR:.2f}s)")


def _sine(freq, dur, vol=0.5):
    return [vol * 32767 * math.sin(2 * math.pi * freq * i / SR)
            for i in range(int(SR * dur))]


def _square(freq, dur, vol=0.3):
    """Band-limited square wave — sum of odd harmonics up to Nyquist."""
    samples = []
    n = int(SR * dur)
    # Number of odd harmonics that fit below Nyquist
    max_harm = int((SR / 2) / freq)
    for i in range(n):
        t = 2 * math.pi * freq * i / SR
        v = 0.0
        for h in range(1, max_harm + 1, 2):  # odd harmonics: 1, 3, 5...
            v += math.sin(h * t) / h
        samples.append(vol * 32767 * v * (4.0 / math.pi))
    return samples


def _noise(dur, vol=0.3):
    return [vol * 32767 * (random.random() * 2 - 1) for _ in range(int(SR * dur))]


def _sweep(f_start, f_end, dur, vol=0.5):
    samples = []
    n = int(SR * dur)
    for i in range(n):
        t = i / SR
        frac = i / n
        freq = f_start + (f_end - f_start) * frac
        samples.append(vol * 32767 * math.sin(2 * math.pi * freq * t))
    return samples


def _square_sweep(f_start, f_end, dur, vol=0.3):
    """Frequency sweep using a band-limited square wave — Game Boy character."""
    samples = []
    n = int(SR * dur)
    for i in range(n):
        t = i / SR
        frac = i / n
        freq = f_start + (f_end - f_start) * frac
        if freq <= 0:
            samples.append(0)
            continue
        max_harm = max(1, int((SR / 2) / freq))
        v = 0.0
        phase = 2 * math.pi * freq * t
        for h in range(1, max_harm + 1, 2):
            v += math.sin(h * phase) / h
        samples.append(vol * 32767 * v * (4.0 / math.pi))
    return samples


def _envelope(samples, attack=0.01, decay=0.05, sustain_level=0.7, release=0.05):
    n = len(samples)
    a_end = int(attack * SR)
    d_end = a_end + int(decay * SR)
    r_start = max(d_end, n - int(release * SR))
    out = []
    for i, s in enumerate(samples):
        if i < a_end:
            env = i / max(a_end, 1)
        elif i < d_end:
            env = 1.0 - (1.0 - sustain_level) * (i - a_end) / max(d_end - a_end, 1)
        elif i < r_start:
            env = sustain_level
        else:
            env = sustain_level * (1.0 - (i - r_start) / max(n - r_start, 1))
        out.append(s * env)
    return out


def _mix(a, b):
    length = max(len(a), len(b))
    out = []
    for i in range(length):
        va = a[i] if i < len(a) else 0
        vb = b[i] if i < len(b) else 0
        out.append(va + vb)
    return out


def _concat(*parts):
    out = []
    for p in parts:
        out.extend(p)
    return out


def _triangle(freq, dur, vol=0.3):
    """Triangle wave — softer than square, good for pads and bass."""
    samples = []
    period = SR / freq
    for i in range(int(SR * dur)):
        phase = (i % period) / period
        if phase < 0.5:
            v = 4.0 * phase - 1.0
        else:
            v = 3.0 - 4.0 * phase
        samples.append(vol * 32767 * v)
    return samples


def _delay(samples, delay_time=0.25, feedback=0.4, mix_level=0.5):
    """Add echo/delay effect for atmosphere."""
    delay_samples = int(delay_time * SR)
    out = list(samples)
    # Extend output to fit the tail
    tail = int(delay_samples * 4)
    out.extend([0] * tail)
    for i in range(delay_samples, len(out)):
        out[i] += out[i - delay_samples] * feedback
    # Mix dry + wet
    result = []
    for i in range(len(out)):
        dry = samples[i] if i < len(samples) else 0
        wet = out[i]
        result.append(dry * (1 - mix_level) + wet * mix_level)
    return result


def _note(freq, dur, wave='sine', vol=0.2, attack=0.01, decay=0.05,
          sustain=0.7, release=0.05):
    """Generate a single enveloped note with chosen waveform."""
    if freq == 0:
        return [0] * int(SR * dur)
    generators = {'sine': _sine, 'square': _square, 'triangle': _triangle}
    raw = generators[wave](freq, dur, vol)
    return _envelope(raw, attack=attack, decay=decay,
                     sustain_level=sustain, release=min(release, dur * 0.4))


def _mix_layers(*layers):
    """Mix multiple sample lists together, extending to longest."""
    if not layers:
        return []
    length = max(len(l) for l in layers)
    out = [0.0] * length
    for layer in layers:
        for i, s in enumerate(layer):
            out[i] += s
    return out


# ── SFX Generators ────────────────────────────────────────────────────

def gen_step():
    """Soft tap with texture — like footsteps on a terminal floor."""
    click = _envelope(_noise(0.02, 0.12),
                      attack=0.001, decay=0.008, sustain_level=0.05, release=0.008)
    tone = _envelope(_triangle(280, 0.025, 0.2),
                     attack=0.002, decay=0.01, sustain_level=0.1, release=0.01)
    _write("sfx_step.wav", _mix(click, tone))


def gen_select():
    """Snappy two-tone boop — Mother-style menu confirm."""
    boop1 = _envelope(_square(660, 0.04, 0.25),
                      attack=0.003, decay=0.015, sustain_level=0.3, release=0.01)
    boop2 = _envelope(_square(880, 0.06, 0.3),
                      attack=0.003, decay=0.02, sustain_level=0.25, release=0.015)
    _write("sfx_select.wav", _concat(boop1, boop2))


def gen_encounter():
    """Pokemon-style encounter — flash burst, rapid descending cascade, sting."""
    # 1. Bright flash burst (short noise + high tone)
    flash_noise = _envelope(_noise(0.04, 0.3),
                            attack=0.001, decay=0.01, sustain_level=0.1, release=0.015)
    flash_tone = _envelope(_square(1200, 0.04, 0.3),
                           attack=0.001, decay=0.015, sustain_level=0.1, release=0.01)
    flash = _mix(flash_noise, flash_tone)

    # 2. Rapid descending cascade — "dee-dee-dee-dee-dee-dee"
    cascade_freqs = [1100, 980, 860, 740, 620, 500, 400, 320]
    note_dur = 0.035
    cascade = []
    for freq in cascade_freqs:
        n = _envelope(_square(freq, note_dur, 0.3),
                      attack=0.002, decay=0.01, sustain_level=0.35, release=0.008)
        cascade.extend(n)

    # 3. Short gap
    gap = [0] * int(SR * 0.04)

    # 4. Final dramatic low sting (chord hit + thump)
    sting_lo = _square(165, 0.12, 0.25)       # E3
    sting_mid = _square(208, 0.12, 0.18)      # G#3
    sting_hi = _square(247, 0.12, 0.15)       # B3
    sting_thump = _sine(70, 0.12, 0.2)
    sting = _envelope(_mix_layers(sting_lo, sting_mid, sting_hi, sting_thump),
                      attack=0.003, decay=0.04, sustain_level=0.4, release=0.05)

    _write("sfx_encounter.wav", _concat(flash, cascade, gap, sting))


def gen_hit():
    """CHUNKY impact — meaty crunch + low thump + pitch bend."""
    # Noise crunch (the "smack")
    crunch = _envelope(_noise(0.08, 0.4),
                       attack=0.001, decay=0.02, sustain_level=0.15, release=0.03)
    # Low impact thump
    thump = _envelope(_sine(80, 0.1, 0.35),
                      attack=0.002, decay=0.04, sustain_level=0.05, release=0.03)
    # Pitch-bend down (the "weight" of the hit)
    bend = _envelope(_sweep(200, 60, 0.1, 0.25),
                     attack=0.002, decay=0.03, sustain_level=0.1, release=0.03)
    _write("sfx_hit.wav", _mix_layers(crunch, thump, bend))


def gen_attack():
    """Whoosh-into-thwack — swing and impact layered."""
    # Fast ascending swoosh (the swing)
    swoosh = _envelope(_sweep(150, 900, 0.1, 0.3),
                       attack=0.005, decay=0.03, sustain_level=0.2, release=0.02)
    # Impact at the end
    impact_noise = _envelope(_noise(0.06, 0.35),
                             attack=0.001, decay=0.015, sustain_level=0.1, release=0.02)
    impact_thud = _envelope(_sine(100, 0.06, 0.3),
                            attack=0.002, decay=0.03, sustain_level=0.05, release=0.015)
    impact = _mix(impact_noise, impact_thud)
    # Small gap then impact
    gap = [0] * int(SR * 0.02)
    _write("sfx_attack.wav", _concat(swoosh, gap, impact))


def gen_heal():
    """Sparkly ascending — PSI-style healing shimmer."""
    # Quick ascending notes with harmonic shimmer, slightly overlapping
    notes = [
        (523, 0.08),   # C5
        (659, 0.08),   # E5
        (784, 0.08),   # G5
        (1047, 0.12),  # C6
    ]
    samples = []
    for freq, dur in notes:
        # Main tone + octave shimmer
        tone = _sine(freq, dur, 0.25)
        shimmer = _sine(freq * 2, dur, 0.08)
        sparkle = _triangle(freq * 1.5, dur, 0.06)
        n = _envelope(_mix_layers(tone, shimmer, sparkle),
                      attack=0.005, decay=0.02, sustain_level=0.5, release=0.025)
        samples.extend(n)
    # Final held shimmer chord
    c6 = _sine(1047, 0.2, 0.15)
    e6 = _sine(1319, 0.2, 0.1)
    g6 = _sine(1568, 0.2, 0.08)
    tail = _envelope(_mix_layers(c6, e6, g6),
                     attack=0.01, decay=0.05, sustain_level=0.3, release=0.1)
    samples.extend(tail)
    _write("sfx_heal.wav", samples)


def gen_text():
    """Crisp click — crunchy square wave for that Mother-style text scroll."""
    click = _square(500, 0.025, 0.12)
    s = _envelope(click, attack=0.001, decay=0.008, sustain_level=0.15, release=0.008)
    _write("sfx_text.wav", s)


def gen_spare():
    """Triumphant resolution — quick arpeggio into a warm held chord."""
    # Fast ascending arpeggio (staccato)
    arp = []
    for freq in [392, 494, 587, 659]:  # G4 B4 D5 E5
        n = _envelope(_square(freq, 0.07, 0.25),
                      attack=0.003, decay=0.02, sustain_level=0.35, release=0.015)
        arp.extend(n)
    # Held major chord with warmth (G major = G4 B4 D5)
    g = _sine(392, 0.35, 0.2)
    b = _sine(494, 0.35, 0.15)
    d = _sine(587, 0.35, 0.15)
    g_oct = _triangle(784, 0.35, 0.08)
    chord = _envelope(_mix_layers(g, b, d, g_oct),
                      attack=0.01, decay=0.08, sustain_level=0.6, release=0.12)
    _write("sfx_spare.wav", _concat(arp, chord))


def gen_save():
    """Warm reassuring chime — ascending with a cozy held tone."""
    # Ascending chime notes (triangle for warmth)
    chime = []
    for freq in [523, 659, 784]:  # C5 E5 G5
        tone = _triangle(freq, 0.09, 0.25)
        shimmer = _sine(freq * 2, 0.09, 0.06)
        n = _envelope(_mix(tone, shimmer),
                      attack=0.005, decay=0.02, sustain_level=0.4, release=0.02)
        chime.extend(n)
    # Final warm held note with octave
    c6 = _triangle(1047, 0.25, 0.2)
    c5 = _sine(523, 0.25, 0.12)
    tail = _envelope(_mix(c6, c5),
                     attack=0.01, decay=0.05, sustain_level=0.5, release=0.1)
    chime.extend(tail)
    _write("sfx_save.wav", chime)


def gen_item():
    """Satisfying bwoop! pickup — quick ascending two-tone with bounce."""
    lo = _envelope(_square(440, 0.04, 0.25),
                   attack=0.003, decay=0.015, sustain_level=0.3, release=0.01)
    hi = _envelope(_square(880, 0.07, 0.3),
                   attack=0.003, decay=0.02, sustain_level=0.35, release=0.02)
    # Tiny shimmer on the high note
    shimmer = _envelope(_sine(1760, 0.07, 0.08),
                        attack=0.005, decay=0.02, sustain_level=0.1, release=0.02)
    hi = _mix(hi, shimmer)
    _write("sfx_item.wav", _concat(lo, hi))


def gen_levelup():
    """BIG fanfare — quick arpeggio into triumphant layered chord."""
    # Fast ascending arpeggio
    arp = []
    for freq in [262, 330, 392, 523, 659]:  # C4 E4 G4 C5 E5
        n = _envelope(_square(freq, 0.055, 0.22),
                      attack=0.003, decay=0.015, sustain_level=0.3, release=0.01)
        arp.extend(n)
    # Triumphant held chord: C major with shimmer
    c5 = _sine(523, 0.45, 0.2)
    e5 = _sine(659, 0.45, 0.15)
    g5 = _sine(784, 0.45, 0.15)
    c6 = _triangle(1047, 0.45, 0.1)
    sparkle = _sine(1568, 0.45, 0.05)  # G6 sparkle
    chord = _envelope(_mix_layers(c5, e5, g5, c6, sparkle),
                      attack=0.01, decay=0.1, sustain_level=0.65, release=0.15)
    _write("sfx_levelup.wav", _concat(arp, chord))


def gen_ominous():
    """Unsettling drone — detuned beating with dissonant overtone."""
    dur = 1.5
    a = _sine(60, dur, 0.18)
    b = _sine(63, dur, 0.18)
    # Add a high dissonant whisper
    c = _sine(113, dur, 0.06)  # Tritone-ish against the bass
    s = _envelope(_mix_layers(a, b, c),
                  attack=0.3, decay=0.1, sustain_level=0.6, release=0.4)
    _write("sfx_ominous.wav", s)


# ── New SFX (v1.3) ────────────────────────────────────────────────────

def gen_streak():
    """Streak milestone — fast ascending arpeggio, cheerful."""
    arp = []
    for freq in [587, 740, 880, 1175]:  # D5 F#5 A5 D6 — D major up to octave
        tone = _envelope(_square(freq, 0.05, 0.22),
                         attack=0.002, decay=0.01,
                         sustain_level=0.35, release=0.01)
        arp.extend(tone)
    # Tiny sparkle on top
    spark = _envelope(_sine(1760, 0.08, 0.1),
                      attack=0.01, decay=0.02,
                      sustain_level=0.2, release=0.04)
    arp.extend(spark)
    _write("sfx_streak.wav", arp)


def gen_seq_step():
    """Sequence puzzle — single rising chirp for a correct step."""
    s = _envelope(_square_sweep(520, 780, 0.10, 0.22),
                  attack=0.003, decay=0.02,
                  sustain_level=0.35, release=0.02)
    _write("sfx_seq_step.wav", s)


def gen_seq_reject():
    """Sequence puzzle — descending buzz for a wrong press."""
    # Descending square sweep + a dash of noise for grit
    sw = _square_sweep(320, 140, 0.22, 0.28)
    nz = _noise(0.22, 0.08)
    s = _envelope(_mix(sw, nz),
                  attack=0.005, decay=0.04,
                  sustain_level=0.45, release=0.05)
    _write("sfx_seq_reject.wav", s)


def gen_seq_solve():
    """Sequence puzzle — triumphant resolution chord (tritone → major)."""
    # Unresolved two-tone
    lead = _envelope(_square(587, 0.12, 0.28),
                     attack=0.003, decay=0.02,
                     sustain_level=0.4, release=0.02)
    # Resolved D major chord with shimmer
    d = _sine(587, 0.45, 0.2)
    fs = _sine(740, 0.45, 0.15)
    a = _sine(880, 0.45, 0.15)
    d_oct = _triangle(1175, 0.45, 0.10)
    spark = _sine(2349, 0.45, 0.05)
    chord = _envelope(_mix_layers(d, fs, a, d_oct, spark),
                      attack=0.01, decay=0.08,
                      sustain_level=0.65, release=0.15)
    _write("sfx_seq_solve.wav", _concat(lead, chord))


def gen_death():
    """Soul-shatter — sharp break, falling pitch, gritty decay."""
    # Initial shatter: burst of noise + high stab
    stab = _envelope(_square(880, 0.06, 0.3),
                     attack=0.001, decay=0.01,
                     sustain_level=0.5, release=0.03)
    shard = _envelope(_noise(0.08, 0.35),
                      attack=0.001, decay=0.03,
                      sustain_level=0.4, release=0.04)
    crack = _mix(stab, shard)
    # Falling pitch wail — the soul fragments drifting apart
    fall = _envelope(_square_sweep(660, 90, 0.7, 0.3),
                     attack=0.01, decay=0.05,
                     sustain_level=0.7, release=0.2)
    # Low bed for weight
    bed = _envelope(_sine(55, 0.8, 0.18),
                    attack=0.02, decay=0.1,
                    sustain_level=0.6, release=0.3)
    tail = _mix(fall, bed)
    _write("sfx_death.wav", _concat(crack, tail))


def gen_menu_open():
    """UI — quick whoosh for pause menu open/close."""
    s = _envelope(_square_sweep(180, 720, 0.08, 0.22),
                  attack=0.003, decay=0.015,
                  sustain_level=0.3, release=0.02)
    _write("sfx_menu_open.wav", s)


# ── Monster-specific SFX ─────────────────────────────────────────────

def gen_atk_cursor():
    """Digital static burst + glitch stutter for Cursor attack start."""
    burst = _envelope(_noise(0.06, 0.3),
                      attack=0.001, decay=0.02, sustain_level=0.15, release=0.01)
    gap = [0] * int(SR * 0.03)
    stutter1 = _envelope(_square(800, 0.02, 0.2),
                         attack=0.001, decay=0.005, sustain_level=0.1, release=0.005)
    stutter2 = _envelope(_square(600, 0.02, 0.15),
                         attack=0.001, decay=0.005, sustain_level=0.1, release=0.005)
    gap2 = [0] * int(SR * 0.02)
    stutter3 = _envelope(_noise(0.03, 0.2),
                         attack=0.001, decay=0.01, sustain_level=0.05, release=0.005)
    _write("sfx_atk_cursor.wav", _concat(burst, gap, stutter1, gap2, stutter2, gap2, stutter3))


def gen_atk_ping():
    """Rapid ascending beep sequence for Ping attack start."""
    beeps = []
    for freq in [600, 750, 900, 1100, 1400]:
        b = _envelope(_sine(freq, 0.03, 0.25),
                      attack=0.002, decay=0.008, sustain_level=0.2, release=0.005)
        beeps.extend(b)
        beeps.extend([0] * int(SR * 0.015))
    _write("sfx_atk_ping.wav", beeps)


def gen_atk_blob():
    """Low gurgling ooze + rumble for Blob attack start."""
    # Deep rumble
    rumble = _envelope(_sine(45, 0.2, 0.25),
                       attack=0.01, decay=0.05, sustain_level=0.4, release=0.06)
    # Gurgling: rapid random-pitch sine bursts
    gurgle = []
    for _ in range(8):
        freq = random.randint(80, 160)
        g = _envelope(_sine(freq, 0.025, 0.15),
                      attack=0.002, decay=0.008, sustain_level=0.1, release=0.005)
        gurgle.extend(g)
    # Mix rumble and gurgle
    _write("sfx_atk_blob.wav", _mix_layers(rumble, gurgle))


def gen_atk_null():
    """Void whoosh — reverse-like sweep into silence for Null attack start."""
    sweep = _envelope(_sweep(800, 40, 0.25, 0.2),
                      attack=0.15, decay=0.05, sustain_level=0.3, release=0.05)
    whisper = _envelope(_noise(0.25, 0.06),
                        attack=0.1, decay=0.05, sustain_level=0.1, release=0.1)
    tail = [0] * int(SR * 0.1)
    _write("sfx_atk_null.wav", _concat(_mix(sweep, whisper), tail))


def gen_blt_cursor():
    """Short digital click/tick for Cursor bullet spawn."""
    click = _envelope(_square(1200, 0.012, 0.15),
                      attack=0.001, decay=0.004, sustain_level=0.05, release=0.003)
    _write("sfx_blt_cursor.wav", click)


def gen_blt_ping():
    """Quick high 'pip' for Ping bullet spawn."""
    pip = _envelope(_sine(1800, 0.018, 0.15),
                    attack=0.001, decay=0.006, sustain_level=0.08, release=0.004)
    _write("sfx_blt_ping.wav", pip)


def gen_blt_blob():
    """Soft bubble pop for Blob bullet spawn."""
    pop = _envelope(_sine(400, 0.025, 0.12),
                    attack=0.001, decay=0.01, sustain_level=0.06, release=0.008)
    click = _envelope(_noise(0.008, 0.08),
                      attack=0.001, decay=0.003, sustain_level=0.02, release=0.002)
    _write("sfx_blt_blob.wav", _mix(pop, click))


def gen_blt_null():
    """Gentle water drip for Null bullet spawn."""
    drip = _envelope(_sine(1000, 0.02, 0.1),
                     attack=0.001, decay=0.008, sustain_level=0.04, release=0.006)
    body = _envelope(_sine(500, 0.03, 0.06),
                     attack=0.005, decay=0.01, sustain_level=0.03, release=0.008)
    _write("sfx_blt_null.wav", _concat(drip, body))


def gen_atk_daemon():
    """Deep system alert — low alarm sweep + static burst for Daemon attack start."""
    alarm = _envelope(_sweep(120, 60, 0.2, 0.25),
                      attack=0.01, decay=0.05, sustain_level=0.3, release=0.05)
    alarm2 = _envelope(_sweep(200, 80, 0.15, 0.2),
                       attack=0.02, decay=0.04, sustain_level=0.25, release=0.04)
    static = _envelope(_noise(0.1, 0.2),
                       attack=0.005, decay=0.03, sustain_level=0.1, release=0.03)
    thump = _envelope(_sine(45, 0.15, 0.3),
                      attack=0.005, decay=0.06, sustain_level=0.05, release=0.04)
    _write("sfx_atk_daemon.wav", _mix_layers(alarm, alarm2, static, thump))


def gen_blt_daemon():
    """Sharp digital tick — heavier than other bullet sounds."""
    tick = _envelope(_square(900, 0.02, 0.18),
                     attack=0.001, decay=0.006, sustain_level=0.08, release=0.004)
    body = _envelope(_sine(200, 0.025, 0.1),
                     attack=0.002, decay=0.008, sustain_level=0.04, release=0.005)
    click = _envelope(_noise(0.01, 0.1),
                      attack=0.001, decay=0.004, sustain_level=0.02, release=0.003)
    _write("sfx_blt_daemon.wav", _mix_layers(tick, body, click))


def gen_critical():
    """Meaty crunch + high sparkle — SMAAASH! for perfect timing."""
    crunch = _envelope(_noise(0.06, 0.4),
                       attack=0.001, decay=0.015, sustain_level=0.15, release=0.02)
    thump = _envelope(_sine(70, 0.08, 0.3),
                      attack=0.002, decay=0.03, sustain_level=0.05, release=0.02)
    sparkle1 = _envelope(_sine(1400, 0.1, 0.12),
                         attack=0.005, decay=0.03, sustain_level=0.08, release=0.03)
    sparkle2 = _envelope(_sine(2100, 0.08, 0.08),
                         attack=0.008, decay=0.02, sustain_level=0.05, release=0.02)
    _write("sfx_critical.wav", _mix_layers(crunch, thump, sparkle1, sparkle2))


def gen_whiff():
    """Weak whooshy puff for bad timing."""
    puff = _envelope(_noise(0.1, 0.1),
                     attack=0.01, decay=0.03, sustain_level=0.04, release=0.04)
    sweep = _envelope(_sweep(300, 150, 0.1, 0.06),
                      attack=0.01, decay=0.03, sustain_level=0.03, release=0.03)
    _write("sfx_whiff.wav", _mix(puff, sweep))


def gen_atk_pkmn():
    """Electric zap attack start — sharp rising square sweep + crackle + static tail."""
    zap = _envelope(_square_sweep(200, 1200, 0.08, 0.3),
                    attack=0.002, decay=0.02, sustain_level=0.4, release=0.015)
    crackle = _envelope(_noise(0.04, 0.25),
                        attack=0.001, decay=0.01, sustain_level=0.1, release=0.01)
    static = _envelope(_noise(0.06, 0.12),
                       attack=0.005, decay=0.02, sustain_level=0.05, release=0.02)
    _write("sfx_atk_pkmn.wav", _concat(zap, crackle, static))


def gen_blt_pkmn():
    """Electric spark bullet spawn — quick high zap + tiny crackle."""
    zap = _envelope(_square(1500, 0.015, 0.2),
                    attack=0.001, decay=0.005, sustain_level=0.1, release=0.003)
    crackle = _envelope(_noise(0.008, 0.1),
                        attack=0.001, decay=0.003, sustain_level=0.03, release=0.002)
    _write("sfx_blt_pkmn.wav", _concat(zap, crackle))


def gen_cry_pkmn():
    """Game Boy Pikachu cry (~0.6s) — descending + ascending square sweeps."""
    # Descending square sweep
    part1 = _envelope(_square_sweep(800, 300, 0.2, 0.25),
                      attack=0.005, decay=0.04, sustain_level=0.5, release=0.03)
    # Brief gap
    gap = [0] * int(SR * 0.03)
    # Ascending square sweep
    part2 = _envelope(_square_sweep(400, 900, 0.15, 0.2),
                      attack=0.005, decay=0.03, sustain_level=0.4, release=0.025)
    # Short noise tail
    tail = _envelope(_noise(0.05, 0.08),
                     attack=0.003, decay=0.015, sustain_level=0.03, release=0.015)
    _write("sfx_cry_pkmn.wav", _concat(part1, gap, part2, tail))


# ── BGM Generators ────────────────────────────────────────────────────

def gen_bgm_title():
    """'Recovery Console' — title theme for the boot screen, D minor, 96 BPM.

    The title screen is not an adventure space yet; it is a machine waiting
    for a child process to be scheduled. The loop keeps a soft terminal pulse,
    cold arpeggios, and a short unresolved melody so the menu feels alive
    without competing with the boot-console text.
    """
    bpm = 96
    quarter = 60.0 / bpm
    eighth = quarter / 2
    sixteenth = quarter / 4
    n_bars = 16
    total_samp = int(SR * n_bars * 4 * quarter)

    def _pad(samples, dur):
        target = int(SR * dur)
        out = list(samples)
        if len(out) < target:
            out.extend([0] * (target - len(out)))
        return out[:target]

    # Dm | Bb | Gm | A7, repeated with small melodic changes.
    arp_patterns = [
        [147, 294, 349, 440, 587, 440, 349, 294],  # Dm
        [117, 233, 294, 349, 466, 349, 294, 233],  # Bb
        [98, 196, 233, 294, 392, 294, 233, 196],   # Gm
        [110, 220, 277, 330, 440, 330, 277, 220],  # A7
    ]

    arp = []
    for bar in range(n_bars):
        pattern = arp_patterns[bar % len(arp_patterns)]
        if bar >= 8:
            pattern = list(reversed(pattern))
        for freq in pattern:
            note = _note(freq, eighth * 0.82, wave='triangle', vol=0.055,
                         attack=0.01, decay=0.04, sustain=0.35, release=0.05)
            arp.extend(_pad(note, eighth))
    arp = _delay(arp, delay_time=eighth * 3, feedback=0.28, mix_level=0.35)

    bass_roots = [73, 58, 49, 55]  # D2, Bb1, G1, A1
    bass = []
    for bar in range(n_bars):
        root = bass_roots[bar % len(bass_roots)]
        fifth = root * 1.5
        for freq in (root, fifth):
            note = _note(freq, quarter * 1.65, wave='triangle', vol=0.10,
                         attack=0.06, decay=0.10, sustain=0.45, release=0.18)
            bass.extend(_pad(note, quarter * 2))

    # Sparse console pulse: two short beeps per bar, like a heartbeat from
    # the archive node.
    pulse = [0] * total_samp
    for bar in range(n_bars):
        bar_start = int(SR * bar * 4 * quarter)
        for beat in (0, 2.5):
            start = bar_start + int(SR * beat * quarter)
            blip = _note(880 if bar % 4 else 1175, sixteenth * 0.8,
                         wave='square', vol=0.045, attack=0.002,
                         decay=0.02, sustain=0.18, release=0.02)
            for i, s in enumerate(blip):
                if start + i < len(pulse):
                    pulse[start + i] += s

    melody_notes = [
        (587, 2), (0, 1), (523, 1), (440, 2), (349, 2),
        (466, 2), (0, 1), (440, 1), (349, 3), (0, 1),
        (392, 2), (466, 1), (440, 1), (392, 2), (294, 2),
        (440, 2), (554, 1), (440, 1), (330, 3), (0, 1),
    ]
    melody = []
    while len(melody) < total_samp:
        for freq, dur_8ths in melody_notes:
            dur = dur_8ths * eighth
            if freq == 0:
                melody.extend([0] * int(SR * dur))
            else:
                note = _note(freq, dur * 0.82, wave='sine', vol=0.105,
                             attack=0.04, decay=0.07, sustain=0.48,
                             release=0.10)
                melody.extend(_pad(note, dur))
            if len(melody) >= total_samp:
                break
    melody = melody[:total_samp]

    pad = []
    pad_chords = [
        (147, 294, 440),  # Dm
        (117, 233, 349),  # Bb
        (98, 196, 294),   # Gm
        (110, 220, 330),  # A7
    ]
    for bar in range(n_bars):
        tones = [_sine(freq, 4 * quarter, 0.018) for freq in pad_chords[bar % 4]]
        chord = _envelope(_mix_layers(*tones), attack=0.25, decay=0.12,
                          sustain_level=0.55, release=0.25)
        pad.extend(chord)

    samples = _mix_layers(
        arp[:total_samp],
        bass[:total_samp],
        pulse[:total_samp],
        melody[:total_samp],
        pad[:total_samp],
    )
    _write("bgm_title.wav", samples[:total_samp])


def gen_bgm_overworld():
    """'Lost Process' — tender bittersweet ruins theme, D minor, 104 BPM.

    Style: Mother 3 'Love Theme' meets Undertale 'Ruins'. Gentle arpeggio
    echoing through empty corridors, warm bass hum, tender melody.
    """
    bpm = 104
    quarter = 60.0 / bpm
    eighth = quarter / 2
    eighth_samp = int(SR * eighth)

    def _pad8(samples):
        out = list(samples)
        if len(out) < eighth_samp:
            out.extend([0] * (eighth_samp - len(out)))
        return out[:eighth_samp]

    # Chord progression: Dm | Bb | Gm | A7 | Dm | F | Bb | A7
    n_bars = 8
    total_dur = n_bars * 4 * quarter
    total_samp = int(SR * total_dur)

    # ── Layer 1: GENTLE ARPEGGIO (triangle — music box in the corridors) ──
    # Up-down arch through chord tones, 8 eighths per bar
    # D4=294 F4=349 A4=440 D5=587 Bb3=233 G3=196 A3=220 C#4=277
    # E4=330 C4=262 F3=175
    arp_patterns = [
        [294, 349, 440, 587, 440, 349, 294, 349],    # Dm: D4 F4 A4 D5 arch
        [233, 294, 349, 466, 349, 294, 233, 294],    # Bb: Bb3 D4 F4 Bb4
        [196, 233, 294, 392, 294, 233, 196, 233],    # Gm: G3 Bb3 D4 G4
        [220, 277, 330, 440, 330, 277, 220, 330],    # A7: A3 C#4 E4 A4
        [294, 349, 440, 587, 440, 349, 294, 440],    # Dm: slight variation
        [175, 220, 262, 349, 262, 220, 175, 220],    # F:  F3 A3 C4 F4
        [233, 294, 349, 440, 349, 294, 233, 349],    # Bb: with A4 color
        [220, 277, 330, 440, 330, 277, 220, 277],    # A7: tension
    ]
    arp_samples = []
    for bar in arp_patterns:
        for freq in bar:
            n = _note(freq, eighth * 0.8, wave='triangle', vol=0.09,
                      attack=0.01, decay=0.03, sustain=0.35, release=0.04)
            arp_samples.extend(_pad8(n))
    # Echo through empty corridors
    arp_samples = _delay(arp_samples, delay_time=eighth * 3,
                         feedback=0.3, mix_level=0.35)

    # ── Layer 2: WARM BASS (triangle — the mainframe's hum) ──
    # Gentle root → 5th half-note movement
    # D3=147 A2=110 Bb2=117 F3=175 G2=98 E3=165 F2=87 C3=131
    bass_notes = [
        (147, 4), (110, 4),    # Dm: D3 → A2
        (117, 4), (175, 4),    # Bb: Bb2 → F3
        (98, 4),  (147, 4),    # Gm: G2 → D3
        (110, 4), (165, 4),    # A7: A2 → E3
        (147, 4), (110, 4),    # Dm
        (87, 4),  (131, 4),    # F:  F2 → C3
        (117, 4), (175, 4),    # Bb
        (110, 4), (165, 4),    # A7
    ]
    bass_samples = []
    for freq, dur_8ths in bass_notes:
        dur = dur_8ths * eighth
        n = _note(freq, dur * 0.9, wave='triangle', vol=0.13,
                  attack=0.04, decay=0.08, sustain=0.55, release=0.1)
        pad_len = int(SR * dur) - len(n)
        n.extend([0] * max(0, pad_len))
        bass_samples.extend(n[:int(SR * dur)])

    # ── Layer 3: TENDER MELODY (sine — the lost process's voice) ──
    # Longer notes, gentle steps with occasional expressive leaps
    # D5=587 E5=659 F5=698 C5=523 C#5=554 Bb4=466 A4=440 G4=392
    # D4=294 E4=330 F4=349
    # Format: (freq, duration_in_eighths)
    melody = [
        # Bar 1 (Dm): gentle opening — rises then settles
        (587, 2), (698, 1), (659, 1), (587, 2), (440, 2),
        # Bar 2 (Bb): answer — reaches up, trails off
        (466, 2), (587, 1), (523, 1), (466, 3), (0, 1),
        # Bar 3 (Gm): descent — wistful
        (392, 2), (466, 1), (440, 1), (392, 2), (294, 2),
        # Bar 4 (A7): tension, breathe
        (440, 2), (554, 1), (440, 1), (330, 3), (0, 1),
        # Bar 5 (Dm): B section — more movement, yearning
        (587, 2), (698, 2), (659, 1), (587, 1), (523, 2),
        # Bar 6 (F): warm resolution moment
        (349, 2), (440, 2), (523, 1), (440, 1), (349, 2),
        # Bar 7 (Bb): gentle climb — hope?
        (466, 2), (440, 1), (466, 1), (587, 2), (523, 2),
        # Bar 8 (A7): unresolved — pulls back to loop
        (440, 2), (0, 1), (392, 1), (440, 3), (0, 1),
    ]
    lead_samples = []
    for freq, dur_8ths in melody:
        dur = dur_8ths * eighth
        if freq == 0:
            lead_samples.extend([0] * int(SR * dur))
        else:
            n = _note(freq, dur * 0.85, wave='sine', vol=0.16,
                      attack=0.03, decay=0.06, sustain=0.55, release=0.08)
            pad_len = int(SR * dur) - len(n)
            n.extend([0] * max(0, pad_len))
            lead_samples.extend(n[:int(SR * dur)])

    # ── Layer 4: SUBTLE PAD (sine — dying system ambiance) ──
    # Very quiet sustained chord tones, one chord per bar
    pad_chords = [
        (294, 440),    # Dm: D4 + A4
        (233, 349),    # Bb: Bb3 + F4
        (196, 294),    # Gm: G3 + D4
        (220, 330),    # A7: A3 + E4
        (294, 440),    # Dm
        (175, 262),    # F:  F3 + C4
        (233, 349),    # Bb
        (220, 330),    # A7
    ]
    bar_dur = 4 * quarter
    pad_samples = []
    for lo, hi in pad_chords:
        t1 = _sine(lo, bar_dur, 0.04)
        t2 = _sine(hi, bar_dur, 0.03)
        bar_pad = _envelope(_mix(t1, t2),
                            attack=0.15, decay=0.1, sustain_level=0.5, release=0.15)
        pad_samples.extend(bar_pad)

    # ── Mix all layers ──
    arp_trimmed = arp_samples[:total_samp]
    bass_samples = bass_samples[:total_samp]
    lead_samples = lead_samples[:total_samp]
    pad_samples = pad_samples[:total_samp]

    samples = _mix_layers(arp_trimmed, bass_samples, lead_samples, pad_samples)
    samples = samples[:total_samp]

    _write("bgm_overworld.wav", samples)


def gen_bgm_battle():
    """'System Breach' — Mother 3-style funky battle groove, A minor, 148 BPM.

    32-bar AABA loop at 16th-note resolution. Layers: funky walking bass
    (triangle), lead riff (square), synth drums, off-beat chord stabs (square),
    running arpeggio (triangle), counter-melody in B section (sine).
    """
    bpm = 148
    quarter = 60.0 / bpm
    sixteenth = quarter / 4
    six_s = int(SR * sixteenth)
    n_bars = 32
    total_samp = int(SR * n_bars * 4 * quarter)

    def _p16(samples):
        out = list(samples)
        if len(out) < six_s:
            out.extend([0] * (six_s - len(out)))
        return out[:six_s]

    def _render(data, wave='triangle', vol=0.14, attack=0.005, decay=0.03,
                sustain=0.5, release=0.02, frac=0.75):
        """Render (freq, dur_in_16ths) tuples to samples."""
        samp = []
        for freq, dur in data:
            ns = six_s * dur
            if freq == 0:
                samp.extend([0] * ns)
            else:
                n = _note(freq, sixteenth * dur * frac, wave=wave, vol=vol,
                          attack=attack, decay=decay, sustain=sustain, release=release)
                p = list(n)
                if len(p) < ns:
                    p.extend([0] * (ns - len(p)))
                samp.extend(p[:ns])
        return samp

    # ── Chord chart (32 bars) ──
    chords = ['Am','G','F','E','Am','C','Dm','E',       # A
              'Am','Em','F','G','Am','C','Dm','E',       # A'
              'F','G','Am','E','Dm','F','G','E',         # B
              'Am','G','F','E','Am','C','Dm','E']        # A''

    # ── Ch1: FUNKY WALKING BASS (triangle) ──
    # A2=110 B2=124 C3=131 Cs3=139 D3=147 E2=82 E3=165
    # F2=87 Fs2=93 G2=98 Gs2=104 G3=196 A3=220 F3=175
    bass = [
        # Section A (bars 0-7)
        (110,2),(0,2),(110,1),(131,1),(0,2),(165,2),(110,2),(0,1),(98,1),(110,2),
        (98,2),(0,2),(124,1),(147,1),(0,2),(98,2),(93,1),(98,1),(0,2),(98,2),
        (87,2),(0,2),(110,1),(131,1),(0,2),(87,2),(82,1),(87,1),(0,2),(87,2),
        (82,2),(0,2),(104,1),(124,1),(165,2),(0,2),(147,1),(82,1),(0,2),(82,2),
        (110,2),(131,2),(0,2),(110,1),(165,1),(0,2),(110,2),(0,2),(110,2),
        (131,2),(0,2),(165,1),(196,1),(0,2),(131,2),(124,1),(131,1),(0,2),(131,2),
        (147,2),(0,2),(147,1),(175,1),(220,2),(0,2),(147,2),(139,1),(147,1),(0,2),
        (82,2),(0,2),(82,1),(104,1),(124,1),(147,1),(0,2),(82,2),(0,2),(82,2),
        # Section A' (bars 8-15)
        (110,2),(0,1),(110,1),(131,2),(0,2),(165,2),(0,1),(98,1),(110,2),(0,2),
        (82,2),(0,2),(98,1),(124,1),(165,2),(0,2),(82,2),(0,2),(82,2),
        (87,2),(87,1),(0,1),(110,2),(131,2),(0,2),(87,2),(82,1),(87,1),(0,2),
        (98,2),(0,1),(98,1),(124,2),(147,2),(0,2),(196,2),(98,2),(0,2),
        (110,2),(0,1),(165,1),(110,2),(0,2),(131,2),(110,2),(0,2),(110,2),
        (131,2),(165,2),(0,2),(196,2),(131,2),(0,2),(124,1),(131,1),(0,2),
        (147,2),(0,1),(175,1),(220,2),(0,2),(147,2),(0,2),(139,1),(147,1),(0,2),
        (82,2),(104,2),(124,2),(147,2),(165,2),(0,2),(82,2),(0,2),
        # Section B (bars 16-23)
        (87,2),(0,1),(87,1),(110,2),(131,2),(0,2),(175,2),(87,2),(0,2),
        (98,2),(0,1),(124,1),(147,2),(196,2),(0,2),(98,2),(0,2),(98,2),
        (110,2),(165,2),(110,2),(0,2),(131,2),(110,2),(0,2),(110,2),
        (82,2),(0,2),(104,2),(124,2),(82,2),(0,2),(165,2),(82,2),
        (147,2),(0,2),(175,2),(220,2),(147,2),(0,2),(139,2),(147,2),
        (87,2),(110,2),(131,2),(0,2),(87,2),(0,2),(175,2),(87,2),
        (98,2),(124,2),(147,2),(196,2),(98,2),(0,2),(196,2),(98,2),
        (82,2),(0,2),(82,1),(104,1),(124,1),(147,1),(165,2),(82,2),(0,2),(82,2),
        # Section A'' (bars 24-31) — reprise, last 2 bars have fills
        (110,2),(0,2),(110,1),(131,1),(0,2),(165,2),(110,2),(0,1),(98,1),(110,2),
        (98,2),(0,2),(124,1),(147,1),(0,2),(98,2),(93,1),(98,1),(0,2),(98,2),
        (87,2),(0,2),(110,1),(131,1),(0,2),(87,2),(82,1),(87,1),(0,2),(87,2),
        (82,2),(0,2),(104,1),(124,1),(165,2),(0,2),(147,1),(82,1),(0,2),(82,2),
        (110,2),(131,2),(0,2),(110,1),(165,1),(0,2),(110,2),(0,2),(110,2),
        (131,2),(0,2),(165,1),(196,1),(0,2),(131,2),(124,1),(131,1),(0,2),(131,2),
        (147,1),(175,1),(220,1),(175,1),(147,2),(0,2),(139,1),(147,1),(175,1),(220,1),(147,2),(0,2),
        (82,1),(104,1),(124,1),(147,1),(165,1),(147,1),(124,1),(104,1),(82,2),(0,2),(165,2),(82,2),
    ]
    bass_samples = _render(bass, wave='triangle', vol=0.16, attack=0.008,
                           decay=0.03, sustain=0.5, release=0.03, frac=0.75)

    # ── Ch2: LEAD RIFF (square) ──
    # E4=330 F4=349 G4=392 Gs4=415 A4=440 B4=494 C5=523
    # D5=587 E5=659 F5=698 G5=784 Gs5=831 A5=880
    lead = [
        # Section A (bars 0-7) — establish the hook
        (659,2),(0,1),(440,1),(523,1),(659,3),(0,1),(587,2),(0,1),(523,1),(0,3),
        (587,2),(0,1),(392,1),(494,1),(587,3),(0,1),(523,2),(494,2),(0,3),
        (523,3),(0,1),(349,1),(440,1),(523,1),(587,1),(523,2),(0,2),(440,2),(0,2),
        (494,2),(415,2),(330,2),(0,2),(494,2),(659,2),(0,2),(0,2),
        (880,2),(659,1),(0,1),(523,1),(440,1),(0,2),(523,2),(659,2),(0,2),(0,2),
        (784,2),(0,2),(659,1),(523,1),(392,2),(0,2),(523,2),(659,2),(0,2),
        (698,2),(587,2),(0,2),(440,2),(587,2),(698,2),(0,2),(587,2),
        (659,2),(0,2),(415,1),(494,1),(659,2),(831,4),(0,2),(0,2),
        # Section A' (bars 8-15) — variation, climbing
        (659,2),(0,1),(523,1),(440,1),(523,1),(659,2),(0,2),(587,2),(0,2),(0,2),
        (494,2),(0,1),(330,1),(392,1),(494,3),(0,1),(392,2),(330,2),(0,3),
        (523,3),(0,1),(440,1),(349,1),(440,2),(523,2),(587,2),(523,2),(0,2),
        (392,2),(494,2),(587,2),(0,2),(784,4),(587,2),(0,2),
        (880,2),(0,1),(659,1),(523,1),(659,1),(880,2),(0,2),(784,2),(659,2),(0,2),
        (784,2),(659,2),(0,2),(523,1),(659,1),(784,2),(0,2),(659,2),(0,2),
        (698,2),(587,1),(698,1),(0,2),(587,2),(440,2),(587,2),(698,2),(0,2),
        (659,2),(0,1),(494,1),(415,1),(494,1),(659,2),(831,2),(880,2),(0,2),(0,2),
        # Section B (bars 16-23) — new territory, peak
        (349,2),(440,2),(523,2),(698,2),(0,2),(523,1),(440,1),(349,2),(0,2),
        (392,2),(494,2),(587,2),(784,2),(0,2),(587,1),(494,1),(392,2),(0,2),
        (880,4),(784,2),(659,2),(0,2),(880,2),(0,2),(659,2),
        (831,4),(659,2),(494,2),(0,2),(659,2),(494,2),(0,2),
        (587,2),(440,2),(349,2),(0,2),(587,2),(698,2),(587,2),(0,2),
        (698,2),(523,2),(440,2),(0,2),(523,2),(698,4),(0,2),
        (784,2),(0,1),(587,1),(494,1),(587,1),(784,2),(880,4),(0,2),(784,2),
        (659,2),(0,2),(494,2),(415,2),(330,2),(494,2),(659,2),(0,2),
        # Section A'' (bars 24-31) — return + ending fills
        (659,2),(0,1),(440,1),(523,1),(659,3),(0,1),(587,2),(0,1),(523,1),(0,3),
        (587,2),(0,1),(392,1),(494,1),(587,3),(0,1),(523,2),(494,2),(0,3),
        (523,3),(0,1),(349,1),(440,1),(523,1),(587,1),(523,2),(0,2),(440,2),(0,2),
        (494,2),(415,2),(330,2),(0,2),(494,2),(659,2),(0,2),(0,2),
        (880,2),(659,1),(0,1),(523,1),(440,1),(0,2),(523,2),(659,2),(0,2),(0,2),
        (784,2),(0,2),(659,1),(523,1),(392,2),(0,2),(523,2),(659,2),(0,2),
        (698,1),(587,1),(698,1),(587,1),(440,1),(587,1),(698,2),(880,2),(587,2),(0,2),(0,2),
        (659,2),(0,1),(494,1),(415,1),(494,1),(659,2),(831,2),(880,4),(0,2),
    ]
    lead_samples = _render(lead, wave='square', vol=0.14, attack=0.005,
                           decay=0.04, sustain=0.55, release=0.02, frac=0.7)

    # ── Ch3: DRUMS (16th-note patterns) ──
    # K=kick, S=snare, H=closed hat, O=open hat
    drum_A = ['KH','H','H','H','SH','H','KH','H','KH','H','H','H','SH','H','H','O']
    drum_B = ['KH','H','KH','H','SH','H','H','KH','KH','H','KH','H','SH','KH','H','O']
    drum_fill = ['KH','H','SH','H','KH','SH','KH','H','SH','SH','KH','KH','SH','SH','SH','KH']
    drum_map = (
        [drum_A]*7 + [drum_fill]
        + [drum_A]*3 + [drum_B]*4 + [drum_fill]
        + [drum_B]*7 + [drum_fill]
        + [drum_A]*5 + [drum_B]*2 + [drum_fill]
    )

    # Pre-compute drum sounds
    kick_t = _envelope(_sine(55, sixteenth * 3, 0.2),
                       attack=0.002, decay=0.04, sustain_level=0.05, release=0.02)
    kick_c = _envelope(_noise(sixteenth * 0.8, 0.08),
                       attack=0.001, decay=0.015, sustain_level=0.02, release=0.01)
    kick = _mix(kick_t, kick_c)
    snare_b = _envelope(_noise(sixteenth * 2.5, 0.12),
                        attack=0.002, decay=0.03, sustain_level=0.08, release=0.02)
    snare_t = _envelope(_sine(180, sixteenth * 1.2, 0.06),
                        attack=0.001, decay=0.02, sustain_level=0.01, release=0.01)
    snare = _mix(snare_b, snare_t)
    hh = _envelope(_noise(sixteenth * 0.6, 0.04),
                   attack=0.001, decay=0.01, sustain_level=0.01, release=0.005)
    oh = _envelope(_noise(sixteenth * 2.5, 0.05),
                   attack=0.001, decay=0.04, sustain_level=0.02, release=0.02)

    perc_samples = []
    for bar_idx in range(n_bars):
        pattern = drum_map[bar_idx]
        for hits in pattern:
            hit = [0.0] * six_s
            if 'K' in hits:
                for i in range(min(len(kick), six_s)):
                    hit[i] += kick[i]
            if 'S' in hits:
                for i in range(min(len(snare), six_s)):
                    hit[i] += snare[i]
            if 'H' in hits:
                for i in range(min(len(hh), six_s)):
                    hit[i] += hh[i]
            if 'O' in hits:
                for i in range(min(len(oh), six_s)):
                    hit[i] += oh[i]
            perc_samples.extend(_p16(hit))

    # ── Ch4: OFF-BEAT CHORD STABS (square) ──
    stab_v = {
        'Am': (440,523,659), 'G': (392,494,587), 'F': (349,440,523),
        'E': (330,415,494), 'C': (523,659,784), 'Dm': (294,349,440),
        'Em': (330,392,494),
    }
    stab_samples = []
    for bar_idx in range(n_bars):
        freqs = stab_v[chords[bar_idx]]
        for pos in range(16):
            if pos in (2, 10):
                tones = [_note(f, sixteenth * 0.3, wave='square', vol=0.04,
                               attack=0.003, decay=0.02, sustain=0.25, release=0.02)
                         for f in freqs]
                stab_samples.extend(_p16(_mix_layers(*tones)))
            else:
                stab_samples.extend([0] * six_s)

    # ── Ch5: RUNNING ARPEGGIO (triangle) ──
    arp_v = {
        'Am': [220,262,330,440], 'G': [196,247,294,392], 'F': [175,220,262,349],
        'E': [165,208,247,330], 'C': [262,330,392,523], 'Dm': [147,175,220,294],
        'Em': [165,196,247,330],
    }
    arp_samples = []
    for bar_idx in range(n_bars):
        r, t, f, o = arp_v[chords[bar_idx]]
        pattern = [r,t,f,o, f,t,r,t, f,o,f,t, r,t,f,o]
        for freq in pattern:
            n = _note(freq, sixteenth * 0.55, wave='triangle', vol=0.08,
                      attack=0.005, decay=0.02, sustain=0.35, release=0.015)
            arp_samples.extend(_p16(n))

    # ── Ch6: COUNTER-MELODY (sine, B section bars 16-23 only) ──
    counter = [
        (349,8),(0,8),          # Bar 16 (F)
        (392,8),(0,8),          # Bar 17 (G)
        (440,12),(0,4),         # Bar 18 (Am)
        (415,8),(330,4),(0,4),  # Bar 19 (E)
        (294,8),(0,8),          # Bar 20 (Dm)
        (349,12),(0,4),         # Bar 21 (F)
        (392,8),(494,4),(0,4),  # Bar 22 (G)
        (330,8),(0,8),          # Bar 23 (E)
    ]
    counter_samp = _render(counter, wave='sine', vol=0.09, attack=0.02,
                           decay=0.05, sustain=0.6, release=0.05, frac=0.85)
    counter_start = 16 * 16 * six_s
    counter_full = [0] * counter_start + counter_samp
    counter_full.extend([0] * max(0, total_samp - len(counter_full)))
    counter_full = counter_full[:total_samp]

    # ── Mix + normalize ──
    bass_samples = bass_samples[:total_samp]
    lead_samples = lead_samples[:total_samp]
    perc_samples = perc_samples[:total_samp]
    stab_samples = stab_samples[:total_samp]
    arp_samples = arp_samples[:total_samp]

    samples = _mix_layers(bass_samples, lead_samples, perc_samples,
                          stab_samples, arp_samples, counter_full)
    samples = samples[:total_samp]

    peak = max(abs(s) for s in samples) if samples else 1
    if peak > 32767:
        scale = 32767 / peak
        samples = [s * scale for s in samples]

    _write("bgm_battle.wav", samples)



def gen_bgm_battle_cursor():
    """'Blinking Anxiety' — Cursor battle theme. E minor, 138 BPM.

    32-bar AABA loop at 16th-note resolution. Obsessive E-E-G-F#-E hook.
    Layers: sparse nervous bass (triangle), stuttering lead (square),
    twitchy minimal drums, glitch texture / chord stabs, arpeggio (triangle).
    """
    bpm = 138
    quarter = 60.0 / bpm
    sixteenth = quarter / 4
    six_s = int(SR * sixteenth)
    n_bars = 32
    total_samp = int(SR * n_bars * 4 * quarter)

    def _p16(samples):
        out = list(samples)
        if len(out) < six_s:
            out.extend([0] * (six_s - len(out)))
        return out[:six_s]

    def _render(data, wave='triangle', vol=0.14, attack=0.005, decay=0.03,
                sustain=0.5, release=0.02, frac=0.75):
        samp = []
        for freq, dur in data:
            ns = six_s * dur
            if freq == 0:
                samp.extend([0] * ns)
            else:
                n = _note(freq, sixteenth * dur * frac, wave=wave, vol=vol,
                          attack=attack, decay=decay, sustain=sustain, release=release)
                p = list(n)
                if len(p) < ns:
                    p.extend([0] * (ns - len(p)))
                samp.extend(p[:ns])
        return samp

    chords = ['Em','Em','C','D','Em','Am','C','B7',
              'Em','Em','C','D','Em','Am','B7','Em',
              'Am','B7','C','D','Em','Am','D','B7',
              'Em','Em','C','D','Em','Am','C','B7']

    # ── Ch1: SPARSE NERVOUS BASS (triangle) ──
    # E2=82 F#2=93 G2=98 A2=110 B2=124 C3=131 D3=147 E3=165
    bass = [
        # Section A (bars 0-7)
        (82,2),(0,4),(165,2),(0,2),(82,2),(0,2),(82,2),
        (0,4),(82,2),(0,2),(124,2),(0,2),(82,2),(0,2),
        (131,2),(0,4),(165,2),(0,2),(131,2),(0,2),(131,2),
        (147,2),(0,2),(147,2),(0,2),(110,2),(0,2),(147,2),(0,2),
        (82,2),(0,4),(165,2),(0,2),(82,1),(98,1),(0,2),(82,2),
        (110,2),(0,4),(82,2),(0,2),(110,2),(0,2),(110,2),
        (131,2),(0,2),(131,2),(0,2),(165,2),(0,2),(131,2),(0,2),
        (124,2),(0,4),(93,2),(0,2),(124,2),(0,2),(124,2),
        # Section A' (bars 8-15) — more active
        (82,2),(0,2),(82,2),(0,2),(165,2),(0,2),(82,2),(0,2),
        (82,1),(0,1),(82,1),(0,1),(0,2),(165,2),(0,2),(82,2),(0,4),
        (131,2),(0,2),(165,2),(0,2),(131,2),(0,2),(131,2),(0,2),
        (147,2),(0,2),(147,2),(110,2),(0,2),(147,2),(0,4),
        (82,2),(165,2),(0,2),(82,2),(0,2),(165,2),(82,2),(0,2),
        (110,2),(0,2),(82,2),(0,2),(110,2),(0,4),(110,2),
        (124,2),(0,2),(93,2),(124,2),(0,2),(124,2),(0,2),(93,2),
        (82,2),(0,4),(165,2),(0,2),(82,2),(0,4),
        # Section B (bars 16-23) — new territory
        (110,2),(0,2),(110,2),(0,2),(82,2),(0,2),(110,2),(0,2),
        (124,2),(0,2),(124,2),(93,2),(0,2),(124,2),(0,4),
        (131,2),(0,2),(165,2),(131,2),(0,2),(131,2),(0,4),
        (147,2),(0,2),(147,2),(0,2),(110,2),(147,2),(0,2),(0,2),
        (82,2),(165,2),(82,2),(0,2),(165,2),(0,2),(82,2),(0,2),
        (110,2),(0,4),(82,2),(0,2),(110,2),(0,4),
        (147,2),(0,2),(147,2),(0,2),(110,1),(147,1),(0,2),(147,2),(0,2),
        (124,2),(0,4),(93,2),(0,2),(124,2),(0,4),
        # Section A'' (bars 24-31) — reprise + fills
        (82,2),(0,4),(165,2),(0,2),(82,2),(0,2),(82,2),
        (0,4),(82,2),(0,2),(124,2),(0,2),(82,2),(0,2),
        (131,2),(0,4),(165,2),(0,2),(131,2),(0,2),(131,2),
        (147,2),(0,2),(147,2),(0,2),(110,2),(0,2),(147,2),(0,2),
        (82,2),(0,4),(165,2),(0,2),(82,1),(98,1),(0,2),(82,2),
        (110,2),(0,4),(82,2),(0,2),(110,2),(0,2),(110,2),
        (131,1),(165,1),(131,1),(0,1),(131,2),(0,2),(165,2),(131,2),(0,4),
        (124,1),(93,1),(124,1),(0,1),(124,2),(0,2),(93,2),(124,2),(0,4),
    ]
    bass_samples = _render(bass, wave='triangle', vol=0.12, attack=0.006,
                           decay=0.025, sustain=0.4, release=0.025, frac=0.6)

    # ── Ch2: STUTTERING LEAD — THE HOOK (square) ──
    # E5=659 F#5=740 G5=784 A5=880 B4=494 C5=523 D5=587
    # E4=330 F#4=370 G4=392 A4=440
    lead = [
        # Section A (bars 0-7)
        (659,2),(659,2),(0,2),(784,2),(740,2),(659,2),(0,4),
        (0,4),(659,1),(0,1),(587,2),(523,2),(0,2),(494,2),(0,2),
        (523,2),(0,2),(440,2),(523,2),(0,2),(440,1),(392,1),(0,4),
        (587,2),(0,1),(494,1),(587,2),(659,2),(0,2),(587,2),(0,2),(0,2),
        (659,2),(659,2),(0,2),(784,2),(740,2),(659,2),(0,4),
        (440,2),(0,2),(330,1),(392,1),(440,2),(0,2),(392,2),(330,2),(0,2),
        (523,2),(659,2),(0,2),(523,1),(440,1),(0,2),(523,2),(0,4),
        (494,2),(0,2),(370,1),(494,1),(587,2),(0,2),(494,2),(0,4),
        # Section A' (bars 8-15) — higher anxiety
        (659,2),(659,1),(0,1),(659,2),(784,2),(740,2),(659,2),(0,4),
        (659,1),(0,1),(659,1),(0,1),(0,2),(784,2),(740,1),(659,1),(0,2),(0,4),
        (523,2),(659,2),(784,2),(0,2),(659,1),(523,1),(0,2),(440,2),(0,2),
        (392,2),(494,2),(587,2),(0,2),(784,4),(587,2),(0,2),
        (880,2),(0,1),(659,1),(784,2),(740,2),(659,2),(0,2),(880,2),(0,2),
        (440,2),(392,2),(330,2),(0,2),(440,2),(523,2),(440,2),(0,2),
        (494,2),(587,2),(659,2),(740,2),(0,2),(587,2),(494,2),(0,2),
        (659,2),(0,2),(659,2),(0,4),(523,2),(494,2),(0,2),
        # Section B (bars 16-23) — new emotional territory
        (440,3),(0,1),(523,2),(659,2),(0,2),(523,2),(440,2),(0,2),
        (494,2),(587,2),(740,4),(0,2),(587,2),(494,2),(0,2),
        (523,4),(0,2),(659,2),(784,2),(659,2),(523,2),(0,2),
        (587,2),(659,2),(587,2),(0,2),(440,2),(587,2),(659,2),(0,2),
        (880,4),(784,2),(659,2),(0,2),(784,2),(880,2),(0,2),
        (440,2),(523,2),(440,2),(0,2),(392,2),(330,2),(0,4),
        (587,2),(0,1),(494,1),(587,2),(659,2),(784,2),(659,2),(0,2),(0,2),
        (494,2),(0,2),(370,2),(494,4),(0,2),(587,2),(0,2),
        # Section A'' (bars 24-31) — return + fills
        (659,2),(659,2),(0,2),(784,2),(740,2),(659,2),(0,4),
        (0,4),(659,1),(0,1),(587,2),(523,2),(0,2),(494,2),(0,2),
        (523,2),(0,2),(440,2),(523,2),(0,2),(440,1),(392,1),(0,4),
        (587,2),(0,1),(494,1),(587,2),(659,2),(0,2),(587,2),(0,2),(0,2),
        (659,2),(659,2),(0,2),(784,2),(740,2),(659,2),(0,4),
        (440,2),(0,2),(330,1),(392,1),(440,2),(0,2),(392,2),(330,2),(0,2),
        (523,1),(659,1),(784,1),(659,1),(523,1),(440,1),(523,2),(659,2),(523,2),(0,2),(0,2),
        (494,2),(0,1),(370,1),(494,1),(587,1),(659,2),(740,2),(659,2),(494,2),(0,2),
    ]
    lead_samples = _render(lead, wave='square', vol=0.12, attack=0.004,
                           decay=0.03, sustain=0.5, release=0.015, frac=0.65)

    # ── Ch3: TWITCHY DRUMS ──
    drum_A = ['H','.','H','.','SH','.','.','H','.','H','.','.','SH','.','H','.']
    drum_B = ['KH','.','H','.','SH','.','H','.','.','H','KH','.','SH','.','H','.']
    drum_fill = ['H','S','H','S','H','S','H','S','KH','S','KH','S','KH','SH','SH','KH']
    drum_map = (
        [drum_A]*7 + [drum_fill]
        + [drum_A]*3 + [drum_B]*4 + [drum_fill]
        + [drum_B]*7 + [drum_fill]
        + [drum_A]*5 + [drum_B]*2 + [drum_fill]
    )

    snare_b = _envelope(_noise(sixteenth * 2, 0.1),
                        attack=0.002, decay=0.025, sustain_level=0.06, release=0.015)
    snare_t = _envelope(_sine(200, sixteenth * 1, 0.04),
                        attack=0.001, decay=0.015, sustain_level=0.01, release=0.008)
    snare = _mix(snare_b, snare_t)
    hh = _envelope(_noise(sixteenth * 0.5, 0.035),
                   attack=0.001, decay=0.008, sustain_level=0.008, release=0.004)
    kick_t = _envelope(_sine(50, sixteenth * 2.5, 0.15),
                       attack=0.002, decay=0.035, sustain_level=0.04, release=0.015)
    kick_c = _envelope(_noise(sixteenth * 0.5, 0.06),
                       attack=0.001, decay=0.012, sustain_level=0.015, release=0.008)
    kick = _mix(kick_t, kick_c)

    perc_samples = []
    for bar_idx in range(n_bars):
        for hits in drum_map[bar_idx]:
            hit = [0.0] * six_s
            if 'K' in hits:
                for i in range(min(len(kick), six_s)):
                    hit[i] += kick[i]
            if 'S' in hits:
                for i in range(min(len(snare), six_s)):
                    hit[i] += snare[i]
            if 'H' in hits:
                for i in range(min(len(hh), six_s)):
                    hit[i] += hh[i]
            perc_samples.extend(_p16(hit))

    # ── Ch4: GLITCH TEXTURE (A sections) / CHORD STABS (B section) ──
    stab_v = {
        'Em': (330,392,494), 'Am': (440,523,659), 'B7': (494,622,740),
        'C': (262,330,392), 'D': (294,370,440),
    }
    random.seed(42)
    glitch_samples = []
    for bar_idx in range(n_bars):
        if 16 <= bar_idx < 24:
            freqs = stab_v[chords[bar_idx]]
            for pos in range(16):
                if pos in (2, 10):
                    tones = [_note(f, sixteenth * 0.3, wave='square', vol=0.035,
                                   attack=0.003, decay=0.02, sustain=0.2, release=0.015)
                             for f in freqs]
                    glitch_samples.extend(_p16(_mix_layers(*tones)))
                else:
                    glitch_samples.extend([0] * six_s)
        else:
            for pos in range(16):
                if random.random() < 0.1:
                    g = _envelope(_noise(sixteenth * 0.4, 0.035),
                                  attack=0.001, decay=0.008, sustain_level=0.01, release=0.005)
                    sq = _envelope(_square(2000, sixteenth * 0.15, 0.02),
                                   attack=0.001, decay=0.005, sustain_level=0.005, release=0.003)
                    glitch_samples.extend(_p16(_mix(g, sq)))
                else:
                    glitch_samples.extend([0] * six_s)
    random.seed()

    # ── Ch5: RUNNING ARPEGGIO (triangle) ──
    arp_v = {
        'Em': [165,196,247,330], 'Am': [110,131,165,220], 'B7': [124,156,185,247],
        'C': [131,165,196,262], 'D': [147,185,220,294],
    }
    arp_samples = []
    for bar_idx in range(n_bars):
        r, t, f, o = arp_v[chords[bar_idx]]
        pat = [r,t,f,o, f,t,r,t, f,o,f,t, r,t,f,o]
        for freq in pat:
            n = _note(freq, sixteenth * 0.5, wave='triangle', vol=0.07,
                      attack=0.004, decay=0.018, sustain=0.3, release=0.012)
            arp_samples.extend(_p16(n))

    # ── Mix + normalize ──
    bass_samples = bass_samples[:total_samp]
    lead_samples = lead_samples[:total_samp]
    perc_samples = perc_samples[:total_samp]
    glitch_samples = glitch_samples[:total_samp]
    arp_samples = arp_samples[:total_samp]

    samples = _mix_layers(bass_samples, lead_samples, perc_samples,
                          glitch_samples, arp_samples)
    samples = samples[:total_samp]

    peak = max(abs(s) for s in samples) if samples else 1
    if peak > 32767:
        scale = 32767 / peak
        samples = [s * scale for s in samples]

    _write("bgm_battle_cursor.wav", samples)


def gen_bgm_battle_ping():
    """'Packet Storm' — Ping battle theme. G major, 160 BPM.

    32-bar AABA loop at 16th-note resolution. Bouncy ricocheting melody.
    Layers: bouncy bass (triangle), lead melody (square), light drums,
    ping texture (sine pings), running arpeggio (triangle).
    """
    bpm = 160
    quarter = 60.0 / bpm
    sixteenth = quarter / 4
    six_s = int(SR * sixteenth)
    n_bars = 32
    total_samp = int(SR * n_bars * 4 * quarter)

    def _p16(samples):
        out = list(samples)
        if len(out) < six_s:
            out.extend([0] * (six_s - len(out)))
        return out[:six_s]

    def _render(data, wave='triangle', vol=0.14, attack=0.005, decay=0.03,
                sustain=0.5, release=0.02, frac=0.75):
        samp = []
        for freq, dur in data:
            ns = six_s * dur
            if freq == 0:
                samp.extend([0] * ns)
            else:
                n = _note(freq, sixteenth * dur * frac, wave=wave, vol=vol,
                          attack=attack, decay=decay, sustain=sustain, release=release)
                p = list(n)
                if len(p) < ns:
                    p.extend([0] * (ns - len(p)))
                samp.extend(p[:ns])
        return samp

    chords = ['G','Am','C','D','G','Em','C','D',
              'G','Am','C','D','G','Em','Am','D',
              'C','D','Em','D','C','Am','D','G',
              'G','Am','C','D','G','Em','C','D']

    # ── Ch1: BOUNCY BASS (triangle) ──
    # G2=98 A2=110 B2=124 C3=131 D3=147 E2=82 E3=165
    # F#3=185 G3=196 A3=220
    bass = [
        # Section A (bars 0-7)
        (98,2),(0,2),(196,2),(0,2),(98,2),(0,2),(98,1),(124,1),(98,2),
        (110,2),(0,2),(165,2),(0,2),(110,2),(0,2),(110,2),(0,2),
        (131,2),(0,2),(196,2),(0,2),(131,2),(0,2),(131,1),(147,1),(131,2),
        (147,2),(0,2),(220,2),(0,2),(147,2),(0,2),(147,2),(0,2),
        (98,2),(0,1),(98,1),(196,2),(0,2),(98,2),(0,2),(124,1),(98,1),(0,2),
        (82,2),(0,2),(165,2),(0,2),(82,2),(0,2),(82,2),(0,2),
        (131,2),(0,2),(131,1),(165,1),(196,2),(0,2),(131,2),(0,4),
        (147,2),(0,2),(220,2),(147,2),(0,2),(147,2),(0,4),
        # Section A' (bars 8-15) — more active
        (98,2),(124,2),(0,2),(196,2),(0,2),(98,2),(0,2),(98,2),
        (110,2),(0,1),(110,1),(165,2),(0,2),(110,2),(0,2),(82,2),(0,2),
        (131,2),(0,2),(131,2),(165,2),(196,2),(0,2),(131,2),(0,2),
        (147,2),(0,1),(147,1),(220,2),(147,2),(0,2),(220,2),(147,2),(0,2),
        (98,2),(196,2),(0,2),(98,2),(0,2),(196,2),(98,2),(0,2),
        (82,2),(0,2),(82,2),(0,4),(165,2),(82,2),(0,2),
        (110,2),(0,2),(110,2),(131,2),(165,2),(0,2),(110,2),(0,2),
        (147,2),(220,2),(147,2),(0,2),(147,2),(0,2),(220,2),(0,2),
        # Section B (bars 16-23) — development
        (131,2),(0,2),(131,2),(165,2),(0,2),(196,2),(131,2),(0,2),
        (147,2),(0,2),(220,2),(0,2),(147,2),(0,2),(147,2),(0,2),
        (82,2),(165,2),(82,2),(0,2),(165,2),(0,2),(82,2),(0,2),
        (147,2),(0,4),(147,2),(0,2),(220,2),(147,2),(0,2),
        (131,2),(0,2),(196,2),(131,2),(0,2),(131,2),(0,4),
        (110,2),(0,4),(82,2),(0,2),(110,2),(0,4),
        (147,2),(0,1),(147,1),(220,2),(0,2),(147,2),(0,2),(220,2),(0,2),
        (98,2),(0,2),(196,2),(0,2),(98,2),(0,2),(196,2),(98,2),
        # Section A'' (bars 24-31) — reprise + fills
        (98,2),(0,2),(196,2),(0,2),(98,2),(0,2),(98,1),(124,1),(98,2),
        (110,2),(0,2),(165,2),(0,2),(110,2),(0,2),(110,2),(0,2),
        (131,2),(0,2),(196,2),(0,2),(131,2),(0,2),(131,1),(147,1),(131,2),
        (147,2),(0,2),(220,2),(0,2),(147,2),(0,2),(147,2),(0,2),
        (98,2),(0,1),(98,1),(196,2),(0,2),(98,2),(0,2),(124,1),(98,1),(0,2),
        (82,2),(0,2),(165,2),(0,2),(82,2),(0,2),(82,2),(0,2),
        (131,1),(165,1),(196,1),(165,1),(131,2),(0,2),(131,2),(0,2),(196,2),(0,2),
        (147,1),(220,1),(147,1),(110,1),(147,2),(0,2),(220,2),(147,2),(0,4),
    ]
    bass_samples = _render(bass, wave='triangle', vol=0.16, attack=0.008,
                           decay=0.03, sustain=0.5, release=0.03, frac=0.75)

    # ── Ch2: BOUNCY LEAD MELODY (square) ──
    # G5=784 A5=880 B5=988 C6=1047 D5=587 E5=659 F#5=740
    # D6=1175 G4=392 A4=440 B4=494 C5=523
    lead = [
        # Section A (bars 0-7) — the bounce motif
        (784,2),(0,2),(587,2),(0,2),(784,2),(0,2),(988,2),(784,2),
        (880,2),(0,2),(659,2),(0,2),(880,2),(0,2),(659,2),(440,2),
        (523,2),(659,2),(784,2),(0,2),(659,2),(523,2),(0,2),(392,2),
        (587,2),(0,1),(587,1),(740,2),(0,2),(587,2),(0,2),(784,2),(0,2),
        (784,2),(0,1),(587,1),(784,2),(988,2),(0,2),(784,1),(587,1),(784,2),(0,2),
        (659,2),(0,2),(494,2),(659,2),(0,2),(587,2),(494,2),(0,2),
        (523,2),(587,2),(659,2),(784,2),(0,2),(659,1),(523,1),(392,2),(0,2),
        (587,2),(0,2),(740,2),(587,2),(0,2),(784,2),(0,4),
        # Section A' (bars 8-15) — intensifying
        (784,2),(0,1),(784,1),(587,2),(0,2),(784,2),(988,2),(784,2),(0,2),
        (880,2),(0,1),(659,1),(880,2),(0,2),(659,2),(440,2),(659,2),(0,2),
        (1047,2),(880,2),(784,2),(0,2),(659,2),(523,2),(0,2),(392,2),
        (587,1),(659,1),(740,1),(784,1),(880,1),(784,1),(740,1),(659,1),(587,2),(0,2),(587,2),(0,2),
        (988,2),(0,1),(784,1),(988,2),(1175,2),(0,2),(988,1),(784,1),(988,2),(0,2),
        (659,2),(587,2),(523,2),(494,2),(0,2),(0,2),(0,4),
        (440,2),(523,2),(659,2),(784,2),(0,2),(659,2),(523,2),(0,2),
        (587,2),(740,2),(0,2),(587,2),(0,2),(587,2),(740,2),(0,2),
        # Section B (bars 16-23) — new material
        (523,2),(659,2),(784,3),(0,1),(659,2),(523,2),(0,4),
        (587,2),(740,2),(880,3),(0,1),(740,2),(587,2),(0,4),
        (659,2),(784,2),(880,2),(988,2),(0,2),(880,2),(784,2),(0,2),
        (1175,2),(988,2),(784,2),(587,2),(0,2),(0,2),(0,4),
        (523,2),(0,2),(784,2),(0,2),(523,2),(0,2),(659,2),(784,2),
        (440,4),(0,2),(523,2),(659,2),(0,2),(440,2),(0,2),
        (587,2),(659,2),(740,2),(784,4),(740,2),(587,2),(0,2),
        (784,2),(0,2),(587,2),(392,2),(0,2),(587,2),(784,2),(0,2),
        # Section A'' (bars 24-31) — return + fills
        (784,2),(0,2),(587,2),(0,2),(784,2),(0,2),(988,2),(784,2),
        (880,2),(0,2),(659,2),(0,2),(880,2),(0,2),(659,2),(440,2),
        (523,2),(659,2),(784,2),(0,2),(659,2),(523,2),(0,2),(392,2),
        (587,2),(0,1),(587,1),(740,2),(0,2),(587,2),(0,2),(784,2),(0,2),
        (784,2),(0,1),(587,1),(784,2),(988,2),(0,2),(784,1),(587,1),(784,2),(0,2),
        (659,2),(0,2),(494,2),(659,2),(0,2),(587,2),(494,2),(0,2),
        (523,1),(587,1),(659,1),(784,1),(988,1),(784,1),(659,1),(587,1),(523,2),(0,2),(659,2),(784,2),
        (587,2),(0,1),(740,1),(587,1),(740,1),(880,2),(784,2),(587,2),(0,4),
    ]
    lead_samples = _render(lead, wave='square', vol=0.13, attack=0.005,
                           decay=0.035, sustain=0.5, release=0.02, frac=0.7)

    # ── Ch3: LIGHT BOUNCY DRUMS ──
    drum_A = ['KH','H','H','H','SH','H','KH','H','KH','H','H','H','SH','H','H','H']
    drum_B = ['KH','H','H','KH','SH','H','KH','H','KH','KH','H','H','SH','H','KH','H']
    drum_fill = ['KH','H','SH','KH','KH','H','SH','H','KH','SH','KH','SH','KH','SH','SH','KH']
    drum_map = (
        [drum_A]*7 + [drum_fill]
        + [drum_A]*3 + [drum_B]*4 + [drum_fill]
        + [drum_B]*7 + [drum_fill]
        + [drum_A]*5 + [drum_B]*2 + [drum_fill]
    )

    kick_t = _envelope(_sine(60, sixteenth * 2.5, 0.18),
                       attack=0.002, decay=0.035, sustain_level=0.04, release=0.018)
    kick_c = _envelope(_noise(sixteenth * 0.5, 0.06),
                       attack=0.001, decay=0.012, sustain_level=0.015, release=0.008)
    kick = _mix(kick_t, kick_c)
    snare_b = _envelope(_noise(sixteenth * 1.8, 0.09),
                        attack=0.002, decay=0.025, sustain_level=0.06, release=0.015)
    snare_t = _envelope(_sine(190, sixteenth * 0.8, 0.04),
                        attack=0.001, decay=0.015, sustain_level=0.008, release=0.008)
    snare = _mix(snare_b, snare_t)
    hh = _envelope(_noise(sixteenth * 0.5, 0.03),
                   attack=0.001, decay=0.008, sustain_level=0.008, release=0.004)

    perc_samples = []
    for bar_idx in range(n_bars):
        for hits in drum_map[bar_idx]:
            hit = [0.0] * six_s
            if 'K' in hits:
                for i in range(min(len(kick), six_s)):
                    hit[i] += kick[i]
            if 'S' in hits:
                for i in range(min(len(snare), six_s)):
                    hit[i] += snare[i]
            if 'H' in hits:
                for i in range(min(len(hh), six_s)):
                    hit[i] += hh[i]
            perc_samples.extend(_p16(hit))

    # ── Ch4: PING TEXTURE (literal ping sounds on off-beats of odd bars) ──
    # + chord stabs in B section
    stab_v = {
        'G': (392,494,587), 'Am': (440,523,659), 'C': (523,659,784),
        'D': (294,370,440), 'Em': (330,392,494),
    }
    ping_samples = []
    for bar_idx in range(n_bars):
        if 16 <= bar_idx < 24:
            freqs = stab_v[chords[bar_idx]]
            for pos in range(16):
                if pos in (2, 10):
                    tones = [_note(f, sixteenth * 0.3, wave='square', vol=0.035,
                                   attack=0.003, decay=0.02, sustain=0.2, release=0.015)
                             for f in freqs]
                    ping_samples.extend(_p16(_mix_layers(*tones)))
                else:
                    ping_samples.extend([0] * six_s)
        else:
            for pos in range(16):
                if bar_idx % 2 == 0 and pos in (3, 9):
                    p = _note(1568, sixteenth * 0.25, wave='sine', vol=0.06,
                              attack=0.003, decay=0.015, sustain=0.15, release=0.01)
                    ping_samples.extend(_p16(p))
                else:
                    ping_samples.extend([0] * six_s)

    # ── Ch5: RUNNING ARPEGGIO (triangle) ──
    arp_v = {
        'G': [196,247,294,392], 'Am': [220,262,330,440], 'C': [262,330,392,523],
        'D': [147,185,220,294], 'Em': [165,196,247,330],
    }
    arp_samples = []
    for bar_idx in range(n_bars):
        r, t, f, o = arp_v[chords[bar_idx]]
        pat = [r,t,f,o, f,t,r,t, f,o,f,t, r,t,f,o]
        for freq in pat:
            n = _note(freq, sixteenth * 0.5, wave='triangle', vol=0.08,
                      attack=0.005, decay=0.018, sustain=0.35, release=0.012)
            arp_samples.extend(_p16(n))

    # ── Mix + normalize ──
    bass_samples = bass_samples[:total_samp]
    lead_samples = lead_samples[:total_samp]
    perc_samples = perc_samples[:total_samp]
    ping_samples = ping_samples[:total_samp]
    arp_samples = arp_samples[:total_samp]

    samples = _mix_layers(bass_samples, lead_samples, perc_samples,
                          ping_samples, arp_samples)
    samples = samples[:total_samp]

    peak = max(abs(s) for s in samples) if samples else 1
    if peak > 32767:
        scale = 32767 / peak
        samples = [s * scale for s in samples]

    _write("bgm_battle_ping.wav", samples)


def gen_bgm_battle_blob():
    """'Heap Corruption' — Blob battle theme. C minor, 108 BPM.

    32-bar AABA loop at 16th-note resolution. Heavy, chromatic, oozing.
    Layers: detuned bass pair (triangle), wobble lead (sine w/ 4Hz vibrato),
    heavy drums (kick+snare only, no hi-hat), oppressive drone, arpeggio.
    """
    bpm = 108
    quarter = 60.0 / bpm
    sixteenth = quarter / 4
    six_s = int(SR * sixteenth)
    n_bars = 32
    total_samp = int(SR * n_bars * 4 * quarter)

    def _p16(samples):
        out = list(samples)
        if len(out) < six_s:
            out.extend([0] * (six_s - len(out)))
        return out[:six_s]

    chords = ['Cm','Cm','Ab','Bb','Cm','Fm','Ab','G',
              'Cm','Cm','Eb','Fm','Cm','Ab','Bb','G',
              'Ab','Bb','Cm','G','Fm','Ab','Eb','G',
              'Cm','Cm','Ab','Bb','Cm','Fm','Ab','G']

    # ── Ch1: DETUNED BASS PAIR (two triangles 8 cents apart) ──
    # C2=65 Eb2=78 F2=87 G2=98 Ab2=104 Bb2=117 C3=131
    # Notes defined as (freq, dur_in_16ths), rendered as detuned pair
    bass_notes = [
        # Section A (bars 0-7) — slow, heavy, sustained notes
        (65,4),(0,4),(65,2),(78,2),(0,2),(65,2),
        (65,4),(0,2),(98,2),(0,2),(65,4),(0,2),
        (104,4),(0,4),(104,2),(0,2),(87,2),(0,2),
        (117,4),(0,2),(117,2),(0,2),(98,2),(0,4),
        (65,4),(0,2),(65,2),(78,2),(98,2),(0,2),(65,2),
        (87,4),(0,4),(87,2),(0,2),(65,2),(0,2),
        (104,4),(0,2),(104,2),(117,2),(0,2),(104,2),(0,2),
        (98,4),(0,4),(98,2),(0,2),(65,2),(0,2),
        # Section A' (bars 8-15) — slightly more active
        (65,4),(65,2),(0,2),(78,2),(0,2),(65,2),(0,2),
        (65,2),(0,2),(98,2),(65,2),(0,2),(65,4),(0,2),
        (78,4),(0,2),(78,2),(117,2),(0,2),(78,2),(0,2),
        (87,4),(0,2),(87,2),(0,2),(87,2),(65,2),(0,2),
        (65,4),(0,2),(78,2),(98,2),(65,2),(0,2),(65,2),
        (104,4),(0,4),(87,2),(0,2),(104,2),(0,2),
        (117,4),(0,2),(117,2),(0,2),(98,2),(0,2),(117,2),
        (98,4),(0,2),(98,2),(65,2),(0,2),(98,2),(0,2),
        # Section B (bars 16-23) — heavier
        (104,4),(0,2),(104,2),(117,2),(131,2),(0,2),(104,2),
        (117,4),(0,2),(117,2),(0,2),(98,2),(0,2),(117,2),
        (65,4),(98,2),(65,2),(0,2),(78,2),(0,2),(65,2),
        (98,4),(0,4),(98,2),(65,2),(0,2),(0,2),
        (87,4),(0,2),(87,2),(65,2),(0,2),(87,2),(0,2),
        (104,4),(0,2),(104,2),(0,2),(87,2),(0,2),(104,2),
        (78,4),(0,2),(78,2),(117,2),(0,2),(78,2),(0,2),
        (98,4),(0,4),(65,2),(98,2),(0,2),(0,2),
        # Section A'' (bars 24-31) — reprise + fills
        (65,4),(0,4),(65,2),(78,2),(0,2),(65,2),
        (65,4),(0,2),(98,2),(0,2),(65,4),(0,2),
        (104,4),(0,4),(104,2),(0,2),(87,2),(0,2),
        (117,4),(0,2),(117,2),(0,2),(98,2),(0,4),
        (65,4),(0,2),(65,2),(78,2),(98,2),(0,2),(65,2),
        (87,4),(0,4),(87,2),(0,2),(65,2),(0,2),
        (104,2),(117,2),(131,2),(117,2),(104,2),(0,2),(87,2),(0,2),
        (98,1),(65,1),(98,1),(65,1),(98,2),(0,2),(65,2),(98,2),(0,4),
    ]

    # Render detuned bass pair: freq and freq*1.008
    bass_samples = []
    for freq, dur in bass_notes:
        ns = six_s * dur
        if freq == 0:
            bass_samples.extend([0] * ns)
        else:
            dur_s = sixteenth * dur * 0.85
            t1 = _note(freq, dur_s, wave='triangle', vol=0.15,
                       attack=0.015, decay=0.04, sustain=0.6, release=0.04)
            t2 = _note(freq * 1.008, dur_s, wave='triangle', vol=0.11,
                       attack=0.015, decay=0.04, sustain=0.6, release=0.04)
            mixed = _mix(t1, t2)
            if len(mixed) < ns:
                mixed.extend([0] * (ns - len(mixed)))
            bass_samples.extend(mixed[:ns])

    # ── Ch2: WOBBLE LEAD (sine with 4Hz vibrato) — chromatic grind ──
    # C4=262 Eb4=311 F4=349 Gb4=370 G4=392 Ab4=415 Bb4=466
    # C5=523 Eb5=622 G5=784
    lead_notes = [
        # Section A (bars 0-7) — the chromatic grind: C-Eb-F-Gb-G
        (262,2),(0,2),(311,2),(0,2),(349,2),(370,2),(392,4),
        (0,16),
        (262,2),(0,2),(311,2),(0,2),(349,2),(370,2),(392,4),
        (311,4),(0,4),(262,4),(0,4),
        (262,2),(0,2),(311,2),(349,2),(370,2),(392,2),(0,4),
        (349,4),(0,4),(311,4),(0,4),
        (392,4),(370,2),(349,2),(311,4),(262,2),(0,2),
        (0,16),
        # Section A' (bars 8-15) — higher register
        (262,2),(0,1),(262,1),(311,2),(0,2),(349,2),(370,2),(392,2),(0,2),
        (392,4),(0,4),(311,2),(262,2),(0,4),
        (466,2),(0,2),(392,2),(0,2),(349,2),(311,2),(262,2),(0,2),
        (349,4),(0,2),(370,2),(392,4),(0,4),
        (523,2),(0,2),(466,2),(392,2),(0,2),(349,2),(311,2),(262,2),
        (311,4),(0,4),(262,4),(0,4),
        (392,2),(370,2),(349,2),(311,2),(262,2),(0,2),(0,4),
        (0,16),
        # Section B (bars 16-23) — peak + descend
        (262,2),(311,2),(349,2),(392,2),(466,4),(0,4),
        (523,4),(466,2),(392,2),(0,2),(349,2),(0,4),
        (622,4),(523,2),(466,2),(392,2),(0,2),(0,4),
        (784,4),(622,2),(523,2),(0,2),(392,2),(0,4),
        (466,2),(392,2),(349,2),(0,2),(311,2),(262,2),(0,4),
        (311,4),(0,4),(262,4),(0,4),
        (349,2),(370,2),(392,2),(466,2),(523,4),(0,4),
        (392,4),(0,4),(262,4),(0,4),
        # Section A'' (bars 24-31) — reprise + fills
        (262,2),(0,2),(311,2),(0,2),(349,2),(370,2),(392,4),
        (0,16),
        (262,2),(0,2),(311,2),(0,2),(349,2),(370,2),(392,4),
        (311,4),(0,4),(262,4),(0,4),
        (262,2),(0,2),(311,2),(349,2),(370,2),(392,2),(0,4),
        (349,4),(0,4),(311,4),(0,4),
        (392,1),(370,1),(349,1),(311,1),(262,1),(311,1),(349,1),(370,1),(392,4),(0,4),
        (262,4),(0,4),(0,8),
    ]

    # Render wobble lead: per-sample 4Hz vibrato
    lead_samples = []
    for freq, dur in lead_notes:
        ns = six_s * dur
        if freq == 0:
            lead_samples.extend([0] * ns)
        else:
            dur_s = sixteenth * dur * 0.8
            n_samp = int(SR * dur_s)
            raw = []
            for i in range(n_samp):
                wobble = 1.0 + 0.008 * math.sin(2 * math.pi * 4.0 * i / SR)
                f = freq * wobble
                raw.append(0.13 * 32767 * math.sin(2 * math.pi * f * i / SR))
            env = _envelope(raw, attack=0.015, decay=0.04, sustain_level=0.6, release=0.04)
            if len(env) < ns:
                env.extend([0] * (ns - len(env)))
            lead_samples.extend(env[:ns])

    # ── Ch3: HEAVY DRUMS (no hi-hat — just kick and snare) ──
    drum_A = ['K','.','.','.',  'S','.','.','.',  '.','.','.','.',  'S','.','.','.']
    drum_B = ['K','.','.','S',  'S','.','.','.',  'K','.','.','.',  'S','.','K','.']
    drum_fill = ['K','.','K','S',  'K','.','K','S',  'S','S','K','K',  'S','S','S','K']
    drum_map = (
        [drum_A]*7 + [drum_fill]
        + [drum_A]*3 + [drum_B]*4 + [drum_fill]
        + [drum_B]*7 + [drum_fill]
        + [drum_A]*5 + [drum_B]*2 + [drum_fill]
    )

    kick_t = _envelope(_sine(40, sixteenth * 4, 0.25),
                       attack=0.003, decay=0.06, sustain_level=0.06, release=0.03)
    kick_c = _envelope(_noise(sixteenth * 1.0, 0.1),
                       attack=0.001, decay=0.02, sustain_level=0.03, release=0.015)
    kick = _mix(kick_t, kick_c)
    snare_b = _envelope(_noise(sixteenth * 3, 0.14),
                        attack=0.003, decay=0.04, sustain_level=0.08, release=0.025)
    snare_t = _envelope(_sine(150, sixteenth * 1.5, 0.07),
                        attack=0.002, decay=0.025, sustain_level=0.015, release=0.012)
    snare = _mix(snare_b, snare_t)

    perc_samples = []
    for bar_idx in range(n_bars):
        for hits in drum_map[bar_idx]:
            hit = [0.0] * six_s
            if 'K' in hits:
                for i in range(min(len(kick), six_s)):
                    hit[i] += kick[i]
            if 'S' in hits:
                for i in range(min(len(snare), six_s)):
                    hit[i] += snare[i]
            perc_samples.extend(_p16(hit))

    # ── Ch4: OPPRESSIVE DRONE (continuous detuned sines) ──
    drone_dur = n_bars * 4 * quarter
    # Alternate 92/97 Hz per bar for slow beating
    drone_samples = [0.0] * total_samp
    bar_samp = int(SR * 4 * quarter)
    for bar_idx in range(n_bars):
        base_f = 92 if bar_idx % 2 == 0 else 97
        start = bar_idx * bar_samp
        end = min(start + bar_samp, total_samp)
        for i in range(end - start):
            t = i / SR
            v1 = 0.025 * 32767 * math.sin(2 * math.pi * base_f * t)
            v2 = 0.025 * 32767 * math.sin(2 * math.pi * (base_f * 1.5) * t)
            v3 = 0.01 * 32767 * math.sin(2 * math.pi * 370 * t)
            drone_samples[start + i] = v1 + v2 + v3
    # Fade in/out
    fade = int(SR * 0.5)
    for i in range(min(fade, total_samp)):
        drone_samples[i] *= i / fade
    for i in range(min(fade, total_samp)):
        drone_samples[total_samp - 1 - i] *= i / fade

    # ── Ch5: ARPEGGIO (triangle) ──
    arp_v = {
        'Cm': [131,156,196,262], 'Ab': [104,131,156,208], 'Bb': [117,147,175,233],
        'Fm': [87,104,131,175], 'G': [98,124,147,196], 'Eb': [78,98,117,156],
    }
    arp_samples = []
    for bar_idx in range(n_bars):
        r, t, f, o = arp_v[chords[bar_idx]]
        pat = [r,t,f,o, f,t,r,t, f,o,f,t, r,t,f,o]
        for freq in pat:
            n = _note(freq, sixteenth * 0.5, wave='triangle', vol=0.07,
                      attack=0.005, decay=0.02, sustain=0.3, release=0.015)
            arp_samples.extend(_p16(n))

    # ── Mix + normalize ──
    bass_samples = bass_samples[:total_samp]
    lead_samples = lead_samples[:total_samp]
    perc_samples = perc_samples[:total_samp]
    arp_samples = arp_samples[:total_samp]

    samples = _mix_layers(bass_samples, lead_samples, perc_samples,
                          drone_samples, arp_samples)
    samples = samples[:total_samp]

    peak = max(abs(s) for s in samples) if samples else 1
    if peak > 32767:
        scale = 32767 / peak
        samples = [s * scale for s in samples]

    _write("bgm_battle_blob.wav", samples)


def gen_bgm_battle_null():
    """'The Void' — Null battle theme. F# minor, 72 BPM.

    32-bar loop at 16th-note resolution. Achingly sparse, haunting.
    Layers: barely-there bass (sine), sparse melody with delay echo (sine),
    almost-nothing percussion (random noise ticks), 3-voice void drone.
    """
    bpm = 72
    quarter = 60.0 / bpm
    sixteenth = quarter / 4
    six_s = int(SR * sixteenth)
    n_bars = 32
    total_samp = int(SR * n_bars * 4 * quarter)

    def _p16(samples):
        out = list(samples)
        if len(out) < six_s:
            out.extend([0] * (six_s - len(out)))
        return out[:six_s]

    # ── Ch1: BARELY-THERE BASS (sine) ──
    # F#2=93 G#2=104 A2=110 B2=124 C#3=139 D3=147 E3=165 F#3=185
    # Extremely sparse — each note lingers, lots of silence
    bass_notes = [
        # Section A (bars 0-7)
        (93,6),(0,10),
        (0,16),
        (110,6),(0,10),
        (0,16),
        (93,6),(0,10),
        (124,4),(0,12),
        (93,8),(0,8),
        (0,16),
        # Section A' (bars 8-15)
        (93,8),(0,8),
        (0,16),
        (110,6),(0,2),(93,4),(0,4),
        (0,16),
        (93,4),(0,4),(124,4),(0,4),
        (0,16),
        (147,6),(0,10),
        (0,16),
        # Section B (bars 16-23) — slightly more present
        (110,8),(0,8),
        (124,6),(0,10),
        (93,8),(0,8),
        (139,6),(0,10),
        (147,8),(0,8),
        (110,6),(0,10),
        (124,8),(0,8),
        (93,6),(0,10),
        # Section A'' (bars 24-31)
        (93,6),(0,10),
        (0,16),
        (110,6),(0,10),
        (0,16),
        (93,6),(0,10),
        (124,4),(0,12),
        (93,8),(0,8),
        (0,16),
    ]

    bass_samples = []
    for freq, dur in bass_notes:
        ns = six_s * dur
        if freq == 0:
            bass_samples.extend([0] * ns)
        else:
            n = _note(freq, sixteenth * dur * 0.9, wave='sine', vol=0.11,
                      attack=0.05, decay=0.1, sustain=0.5, release=0.15)
            if len(n) < ns:
                n.extend([0] * (ns - len(n)))
            bass_samples.extend(n[:ns])

    # ── Ch2: SPARSE HAUNTING MELODY with DELAY ECHO (sine) ──
    # F#4=370 G#4=415 A4=440 B4=494 C#5=554 D5=587 E5=659 F#5=740
    # Only ~15% of slots have notes — the delay creates the rest
    melody_notes = [
        # Section A (bars 0-7) — establishing loneliness
        (370,4),(0,12),
        (0,8),(554,4),(0,4),
        (440,4),(0,12),
        (0,16),
        (370,4),(0,4),(494,4),(0,4),
        (0,16),
        (659,6),(0,10),
        (0,8),(554,4),(0,4),
        # Section A' (bars 8-15) — slightly more notes
        (370,4),(0,4),(440,4),(0,4),
        (0,8),(494,6),(0,2),
        (554,4),(0,12),
        (0,16),
        (659,4),(0,4),(740,4),(0,4),
        (0,8),(587,4),(0,4),
        (554,4),(0,4),(494,4),(0,4),
        (370,6),(0,10),
        # Section B (bars 16-23) — emotional peak arc
        (440,6),(0,10),
        (494,4),(0,4),(554,6),(0,2),
        (659,8),(0,8),
        (740,6),(0,10),
        (880,8),(0,8),
        (740,4),(0,4),(659,4),(0,4),
        (554,6),(0,10),
        (440,4),(0,4),(370,4),(0,4),
        # Section A'' (bars 24-31) — return to emptiness
        (370,4),(0,12),
        (0,8),(554,4),(0,4),
        (440,4),(0,12),
        (0,16),
        (370,4),(0,4),(494,4),(0,4),
        (0,16),
        (554,6),(0,10),
        (370,8),(0,8),
    ]

    # Render melody raw
    melody_raw = []
    for freq, dur in melody_notes:
        ns = six_s * dur
        if freq == 0:
            melody_raw.extend([0] * ns)
        else:
            # Longer note duration (1.8x slot for bleeding effect)
            n = _note(freq, sixteenth * dur * 1.8, wave='sine', vol=0.16,
                      attack=0.02, decay=0.06, sustain=0.5, release=0.1)
            if len(n) < ns:
                n.extend([0] * (ns - len(n)))
            melody_raw.extend(n[:ns])

    # Apply heavy delay echo
    melody_samples = _delay(melody_raw[:total_samp],
                            delay_time=quarter * 2.5,
                            feedback=0.5,
                            mix_level=0.55)
    melody_samples = melody_samples[:total_samp]

    # ── Ch3: ALMOST-NOTHING PERCUSSION (random noise ticks, 5% probability) ──
    random.seed(77)
    perc_samples = []
    for bar_idx in range(n_bars):
        for pos in range(16):
            if random.random() < 0.05:
                tick = _envelope(_noise(sixteenth * 0.3, 0.025),
                                attack=0.001, decay=0.005, sustain_level=0.005, release=0.003)
                perc_samples.extend(_p16(tick))
            else:
                perc_samples.extend([0] * six_s)
    random.seed()

    # ── Ch4: 3-VOICE VOID DRONE ──
    # F#2=93 + detuned F#2=95.5 (2.5Hz beating) + whisper F#4=370
    drone_samples = [0.0] * total_samp
    for i in range(total_samp):
        t = i / SR
        v1 = 0.025 * 32767 * math.sin(2 * math.pi * 93 * t)
        v2 = 0.025 * 32767 * math.sin(2 * math.pi * 95.5 * t)
        v3 = 0.01 * 32767 * math.sin(2 * math.pi * 370 * t)
        drone_samples[i] = v1 + v2 + v3
    # Slow fade in/out
    fade = int(SR * 1.0)
    for i in range(min(fade, total_samp)):
        drone_samples[i] *= i / fade
    for i in range(min(fade, total_samp)):
        drone_samples[total_samp - 1 - i] *= i / fade

    # ── Mix + normalize ──
    bass_samples = bass_samples[:total_samp]
    melody_samples = melody_samples[:total_samp]
    if len(melody_samples) < total_samp:
        melody_samples.extend([0] * (total_samp - len(melody_samples)))
    perc_samples = perc_samples[:total_samp]

    samples = _mix_layers(bass_samples, melody_samples, perc_samples, drone_samples)
    samples = samples[:total_samp]

    peak = max(abs(s) for s in samples) if samples else 1
    if peak > 32767:
        scale = 32767 / peak
        samples = [s * scale for s in samples]

    _write("bgm_battle_null.wav", samples)


def gen_bgm_battle_daemon():
    """'Heartbreak Protocol' — Daemon boss theme. D minor, 128 BPM.

    32-bar AABA loop at 16th-note resolution. THE boss theme.
    6 layers: driving bass (triangle), passionate lead (square), full drums,
    counter-melody (sine), off-beat chord stabs (square), arpeggio (triangle).
    Core motif: D5-F5-E5-D5.
    """
    bpm = 128
    quarter = 60.0 / bpm
    sixteenth = quarter / 4
    six_s = int(SR * sixteenth)
    n_bars = 32
    total_samp = int(SR * n_bars * 4 * quarter)

    def _p16(samples):
        out = list(samples)
        if len(out) < six_s:
            out.extend([0] * (six_s - len(out)))
        return out[:six_s]

    def _render(data, wave='triangle', vol=0.14, attack=0.005, decay=0.03,
                sustain=0.5, release=0.02, frac=0.75):
        samp = []
        for freq, dur in data:
            ns = six_s * dur
            if freq == 0:
                samp.extend([0] * ns)
            else:
                n = _note(freq, sixteenth * dur * frac, wave=wave, vol=vol,
                          attack=attack, decay=decay, sustain=sustain, release=release)
                p = list(n)
                if len(p) < ns:
                    p.extend([0] * (ns - len(p)))
                samp.extend(p[:ns])
        return samp

    # Dm | Dm | Bb | C | Dm | Dm | Gm | A7
    # Dm | F  | Bb | A7| Dm | Gm | Bb | A7
    # Bb | C  | Dm | A7| Gm | Bb | C  | A7
    # Dm | Dm | Bb | C | Dm | F  | Gm | A7
    chords = ['Dm','Dm','Bb','C','Dm','Dm','Gm','A7',
              'Dm','F','Bb','A7','Dm','Gm','Bb','A7',
              'Bb','C','Dm','A7','Gm','Bb','C','A7',
              'Dm','Dm','Bb','C','Dm','F','Gm','A7']

    # ── Ch1: DRIVING BASS — "the heartbeat" (triangle, loudest bass) ──
    # D2=73 E2=82 F2=87 G2=98 A2=110 Bb2=117 C3=131 D3=147
    bass = [
        # Section A (bars 0-7)
        (147,2),(0,1),(147,1),(73,2),(0,2),(147,2),(0,2),(73,2),(0,2),
        (147,2),(0,2),(73,1),(147,1),(0,2),(147,2),(73,2),(0,2),(0,2),
        (117,2),(0,1),(117,1),(87,2),(0,2),(117,2),(0,2),(87,2),(0,2),
        (131,2),(0,2),(131,1),(82,1),(0,2),(131,2),(82,2),(0,2),(0,2),
        (147,2),(0,1),(147,1),(73,2),(0,2),(147,2),(0,2),(73,1),(147,1),(0,2),
        (147,2),(73,2),(0,2),(147,2),(0,2),(73,2),(147,2),(0,2),
        (98,2),(0,1),(98,1),(73,2),(0,2),(98,2),(0,2),(73,2),(0,2),
        (110,2),(0,2),(110,1),(82,1),(0,2),(110,2),(82,2),(0,2),(0,2),
        # Section A' (bars 8-15) — more intense
        (147,2),(0,1),(73,1),(147,2),(0,2),(73,2),(147,2),(73,2),(0,2),
        (87,2),(0,1),(87,1),(131,2),(0,2),(87,2),(0,2),(131,2),(0,2),
        (117,2),(0,1),(117,1),(87,2),(117,2),(0,2),(87,2),(0,2),(117,2),
        (110,2),(0,2),(82,2),(110,2),(0,2),(82,1),(110,1),(0,2),(110,2),
        (147,2),(73,2),(147,2),(0,2),(73,2),(147,2),(73,2),(0,2),
        (98,2),(0,1),(98,1),(73,2),(0,2),(98,2),(0,2),(73,2),(0,2),
        (117,2),(87,2),(0,2),(117,2),(0,2),(87,2),(117,2),(0,2),
        (110,2),(82,2),(110,2),(0,2),(82,2),(110,2),(82,2),(0,2),
        # Section B (bars 16-23) — even more driving
        (117,2),(0,1),(117,1),(87,2),(0,2),(117,2),(87,2),(117,2),(0,2),
        (131,2),(0,1),(82,1),(131,2),(0,2),(82,2),(131,2),(82,2),(0,2),
        (147,2),(73,2),(147,2),(0,2),(73,2),(147,2),(73,2),(0,2),
        (110,2),(0,2),(82,2),(110,2),(0,2),(82,1),(110,1),(0,2),(110,2),
        (98,2),(0,1),(98,1),(73,2),(0,2),(98,2),(73,2),(98,2),(0,2),
        (117,2),(87,2),(117,2),(0,2),(87,2),(117,2),(0,2),(87,2),
        (131,2),(0,1),(82,1),(131,2),(0,2),(82,2),(131,2),(82,2),(0,2),
        (110,2),(82,2),(110,2),(82,2),(110,2),(0,2),(82,2),(0,2),
        # Section A'' (bars 24-31) — reprise + climax
        (147,2),(0,1),(147,1),(73,2),(0,2),(147,2),(0,2),(73,2),(0,2),
        (147,2),(0,2),(73,1),(147,1),(0,2),(147,2),(73,2),(0,2),(0,2),
        (117,2),(0,1),(117,1),(87,2),(0,2),(117,2),(0,2),(87,2),(0,2),
        (131,2),(0,2),(131,1),(82,1),(0,2),(131,2),(82,2),(0,2),(0,2),
        (147,2),(0,1),(147,1),(73,2),(0,2),(147,2),(0,2),(73,1),(147,1),(0,2),
        (87,2),(0,1),(87,1),(131,2),(0,2),(87,2),(0,2),(131,2),(0,2),
        (98,1),(73,1),(98,1),(73,1),(98,2),(0,2),(73,2),(98,2),(73,2),(0,2),
        (110,1),(82,1),(110,1),(82,1),(110,2),(82,2),(110,2),(82,2),(0,4),
    ]
    bass_samples = _render(bass, wave='triangle', vol=0.18, attack=0.008,
                           decay=0.03, sustain=0.5, release=0.025, frac=0.65)

    # ── Ch2: PASSIONATE LEAD — D-F-E-D motif (square) ──
    # D5=587 E5=659 F5=698 G5=784 A5=880 Bb5=932 C6=1047
    # A4=440 Bb4=466 C5=523 D4=294 E4=330 F4=349
    lead = [
        # Section A (bars 0-7) — THE MOTIF: D-F-E-D
        (587,2),(0,2),(698,2),(659,2),(587,2),(0,2),(0,4),
        (587,2),(0,1),(523,1),(440,2),(0,2),(523,2),(587,2),(0,2),(0,2),
        (466,2),(0,2),(587,2),(523,2),(466,2),(0,2),(0,4),
        (523,2),(0,1),(440,1),(523,2),(587,2),(659,2),(0,2),(523,2),(0,2),
        (587,2),(0,2),(698,2),(659,2),(587,2),(0,2),(523,2),(440,2),
        (587,2),(440,2),(0,2),(587,2),(0,2),(659,2),(587,2),(0,2),
        (392,2),(0,2),(466,2),(440,2),(392,2),(0,2),(0,4),
        (440,2),(0,2),(523,2),(587,2),(659,2),(0,2),(587,2),(0,2),
        # Section A' (bars 8-15) — motif up a third, intensifying
        (587,2),(0,1),(587,1),(698,2),(659,2),(587,2),(0,2),(698,2),(0,2),
        (698,2),(0,2),(880,2),(784,2),(698,2),(0,2),(587,2),(0,2),
        (932,4),(784,2),(698,2),(0,2),(587,2),(0,4),
        (880,2),(0,2),(784,2),(659,2),(0,2),(587,2),(523,2),(0,2),
        (587,2),(698,2),(0,2),(659,2),(587,2),(0,2),(698,2),(880,2),
        (784,2),(0,2),(698,2),(587,2),(0,2),(466,2),(392,2),(0,2),
        (466,2),(523,2),(587,2),(659,2),(698,2),(0,2),(587,2),(0,2),
        (659,2),(0,1),(587,1),(523,1),(587,1),(659,2),(698,2),(784,2),(0,2),(0,2),
        # Section B (bars 16-23) — peak emotional moment
        (466,2),(523,2),(587,2),(698,2),(0,2),(587,2),(523,2),(466,2),
        (523,2),(587,2),(659,2),(784,2),(0,2),(659,2),(587,2),(0,2),
        (880,4),(784,2),(698,2),(0,2),(587,2),(698,2),(880,2),
        (932,4),(880,2),(784,2),(0,2),(698,2),(0,4),
        (784,2),(698,2),(587,2),(0,2),(466,2),(392,2),(0,4),
        (466,2),(523,2),(466,2),(0,2),(392,2),(0,2),(466,2),(0,2),
        (523,2),(587,2),(659,2),(698,2),(784,4),(659,2),(0,2),
        (587,2),(0,2),(440,2),(523,2),(587,2),(659,2),(587,2),(0,2),
        # Section A'' (bars 24-31) — return + epic ending
        (587,2),(0,2),(698,2),(659,2),(587,2),(0,2),(0,4),
        (587,2),(0,1),(523,1),(440,2),(0,2),(523,2),(587,2),(0,2),(0,2),
        (466,2),(0,2),(587,2),(523,2),(466,2),(0,2),(0,4),
        (523,2),(0,1),(440,1),(523,2),(587,2),(659,2),(0,2),(523,2),(0,2),
        (587,2),(0,2),(698,2),(659,2),(587,2),(0,2),(523,2),(440,2),
        (698,2),(0,2),(880,2),(784,2),(698,2),(0,2),(587,2),(0,2),
        (466,1),(523,1),(587,1),(659,1),(698,1),(659,1),(587,1),(523,1),(466,2),(392,2),(0,4),
        (587,2),(0,1),(698,1),(659,1),(587,1),(440,2),(523,2),(587,2),(698,4),
    ]
    lead_samples = _render(lead, wave='square', vol=0.14, attack=0.005,
                           decay=0.04, sustain=0.55, release=0.02, frac=0.7)

    # ── Ch3: FULL DRUMS (with open hi-hat) ──
    drum_A = ['KH','H','H','H','SH','H','KH','H','KH','H','H','H','SH','H','H','O']
    drum_B = ['KH','H','KH','H','SH','H','H','KH','KH','H','KH','H','SH','KH','H','O']
    drum_fill = ['KH','SH','KH','S','KH','SH','KH','SH','S','S','KH','KH','SH','S','SH','KH']
    drum_map = (
        [drum_A]*7 + [drum_fill]
        + [drum_A]*2 + [drum_B]*5 + [drum_fill]
        + [drum_B]*7 + [drum_fill]
        + [drum_A]*4 + [drum_B]*3 + [drum_fill]
    )

    kick_t = _envelope(_sine(50, sixteenth * 3, 0.22),
                       attack=0.002, decay=0.045, sustain_level=0.05, release=0.02)
    kick_c = _envelope(_noise(sixteenth * 0.8, 0.09),
                       attack=0.001, decay=0.015, sustain_level=0.02, release=0.01)
    kick = _mix(kick_t, kick_c)
    snare_b = _envelope(_noise(sixteenth * 2.5, 0.13),
                        attack=0.002, decay=0.03, sustain_level=0.08, release=0.02)
    snare_t = _envelope(_sine(170, sixteenth * 1.2, 0.06),
                        attack=0.001, decay=0.02, sustain_level=0.01, release=0.01)
    snare = _mix(snare_b, snare_t)
    hh = _envelope(_noise(sixteenth * 0.6, 0.04),
                   attack=0.001, decay=0.01, sustain_level=0.01, release=0.005)
    oh = _envelope(_noise(sixteenth * 2.5, 0.055),
                   attack=0.001, decay=0.04, sustain_level=0.02, release=0.02)

    perc_samples = []
    for bar_idx in range(n_bars):
        for hits in drum_map[bar_idx]:
            hit = [0.0] * six_s
            if 'K' in hits:
                for i in range(min(len(kick), six_s)):
                    hit[i] += kick[i]
            if 'S' in hits:
                for i in range(min(len(snare), six_s)):
                    hit[i] += snare[i]
            if 'H' in hits:
                for i in range(min(len(hh), six_s)):
                    hit[i] += hh[i]
            if 'O' in hits:
                for i in range(min(len(oh), six_s)):
                    hit[i] += oh[i]
            perc_samples.extend(_p16(hit))

    # ── Ch4: COUNTER-MELODY (sine — sustained harmonic voice) ──
    # Plays in all sections but more prominent in A' and B
    counter = [
        # Section A (bars 0-7) — subtle harmony
        (440,8),(0,8),  (349,8),(0,8),  (466,8),(0,8),  (523,8),(0,8),
        (440,8),(0,8),  (349,8),(0,8),  (392,8),(0,8),  (330,8),(0,8),
        # Section A' (bars 8-15) — more present
        (440,12),(0,4),  (349,12),(0,4),  (466,8),(587,4),(0,4),  (440,8),(0,8),
        (587,12),(0,4),  (392,8),(466,4),(0,4),  (466,12),(0,4),  (440,8),(330,4),(0,4),
        # Section B (bars 16-23) — full presence
        (466,12),(0,4),  (523,12),(0,4),  (587,12),(0,4),  (659,8),(587,4),(0,4),
        (392,12),(0,4),  (466,12),(0,4),  (523,8),(587,4),(0,4),  (440,8),(0,8),
        # Section A'' (bars 24-31) — return
        (440,8),(0,8),  (349,8),(0,8),  (466,8),(0,8),  (523,8),(0,8),
        (440,8),(0,8),  (349,8),(0,8),  (392,8),(466,4),(0,4),  (440,12),(0,4),
    ]
    counter_samples = _render(counter, wave='sine', vol=0.09, attack=0.02,
                              decay=0.05, sustain=0.6, release=0.05, frac=0.85)

    # ── Ch5: OFF-BEAT CHORD STABS (square — per-bar voicing) ──
    stab_v = {
        'Dm': (294,349,440), 'Bb': (233,294,349), 'C': (262,330,392),
        'Gm': (196,233,294), 'A7': (220,277,330), 'F': (175,220,262),
    }
    stab_samples = []
    for bar_idx in range(n_bars):
        freqs = stab_v[chords[bar_idx]]
        for pos in range(16):
            if pos in (2, 10):
                tones = [_note(f, sixteenth * 0.3, wave='square', vol=0.04,
                               attack=0.003, decay=0.02, sustain=0.25, release=0.02)
                         for f in freqs]
                stab_samples.extend(_p16(_mix_layers(*tones)))
            else:
                stab_samples.extend([0] * six_s)

    # ── Ch6: RUNNING ARPEGGIO (triangle) ──
    arp_v = {
        'Dm': [147,175,220,294], 'Bb': [117,147,175,233], 'C': [131,165,196,262],
        'Gm': [98,117,147,196], 'A7': [110,139,165,220], 'F': [87,110,131,175],
    }
    arp_samples = []
    for bar_idx in range(n_bars):
        r, t, f, o = arp_v[chords[bar_idx]]
        pat = [r,t,f,o, f,t,r,t, f,o,f,t, r,t,f,o]
        for freq in pat:
            n = _note(freq, sixteenth * 0.55, wave='triangle', vol=0.08,
                      attack=0.005, decay=0.02, sustain=0.35, release=0.015)
            arp_samples.extend(_p16(n))

    # ── Mix + normalize ──
    bass_samples = bass_samples[:total_samp]
    lead_samples = lead_samples[:total_samp]
    perc_samples = perc_samples[:total_samp]
    counter_samples = counter_samples[:total_samp]
    stab_samples = stab_samples[:total_samp]
    arp_samples = arp_samples[:total_samp]

    samples = _mix_layers(bass_samples, lead_samples, perc_samples,
                          counter_samples, stab_samples, arp_samples)
    samples = samples[:total_samp]

    peak = max(abs(s) for s in samples) if samples else 1
    if peak > 32767:
        scale = 32767 / peak
        samples = [s * scale for s in samples]

    _write("bgm_battle_daemon.wav", samples)


def gen_bgm_battle_pkmn():
    """'Wild Encounter' — Pokemon Red/Blue Wild Battle theme, C major, 185.5 BPM.

    Faithful 4-channel Game Boy synthesis from the original MIDI transcription.
    Ch1 (square): chromatic 16th-note runs. Ch2 (square): main melody.
    Ch3 (triangle): bass. Ch4 (noise): drum pattern (kick/snare/hi-hat).
    34 bars total. Bars 0-1 (chromatic intro) → sfx_encounter_pkmn.wav.
    Bars 2-33 (loop body) → bgm_battle_pkmn.wav (loops cleanly).
    """
    # ── Tempo and grid ──
    bpm = 185.5
    quarter = 60.0 / bpm          # ~0.3231 sec
    sixteenth = quarter / 4.0     # ~0.0808 sec
    sixteenth_samp = int(SR * sixteenth)

    n_bars = 34
    total_dur = n_bars * 4 * quarter
    total_samp = int(SR * total_dur)
    intro_bars = 2
    intro_samp = int(SR * intro_bars * 4 * quarter)

    def _pad16(samples):
        """Pad/trim to exact 16th-note length."""
        out = list(samples)
        if len(out) < sixteenth_samp:
            out.extend([0] * (sixteenth_samp - len(out)))
        return out[:sixteenth_samp]

    # ── Channel 1: Square wave — chromatic 16th-note runs (vel:75, vol=0.10) ──
    ch1 = [
        (523.25, 1), (493.88, 1), (466.16, 1), (440.0, 1), (466.16, 1), (440.0, 1),
        (415.3, 1), (392.0, 1), (415.3, 1), (392.0, 1), (369.99, 1), (349.23, 1), (369.99, 1),
        (349.23, 1), (329.63, 1), (311.13, 1), (329.63, 1), (311.13, 1), (293.66, 1),
        (277.18, 1), (293.66, 1), (277.18, 1), (261.63, 1), (246.94, 1), (261.63, 1),
        (246.94, 1), (233.08, 1), (220.0, 1), (233.08, 1), (246.94, 1), (261.63, 1),
        (277.18, 1), (392.0, 2), (0, 4), (329.63, 2), (0, 4), (311.13, 2), (0, 10),
        (277.18, 2), (0, 12), (329.63, 2), (0, 4), (311.13, 2), (0, 8), (277.18, 10),
        (392.0, 2), (0, 4), (329.63, 2), (0, 4), (311.13, 2), (0, 10), (277.18, 2), (0, 12),
        (329.63, 2), (0, 4), (311.13, 2), (0, 8), (277.18, 2), (0, 8), (277.18, 1),
        (293.66, 1), (277.18, 1), (261.63, 1), (277.18, 1), (293.66, 1), (277.18, 1),
        (261.63, 1), (277.18, 1), (293.66, 1), (311.13, 1), (293.66, 1), (277.18, 1),
        (261.63, 1), (246.94, 1), (261.63, 1), (277.18, 1), (293.66, 1), (311.13, 1),
        (293.66, 1), (277.18, 1), (293.66, 1), (311.13, 1), (293.66, 1), (277.18, 1),
        (293.66, 1), (311.13, 1), (329.63, 1), (349.23, 1), (329.63, 1), (311.13, 1),
        (293.66, 1), (277.18, 1), (293.66, 1), (311.13, 1), (329.63, 1), (349.23, 1),
        (369.99, 1), (392.0, 1), (415.3, 1), (440.0, 1), (415.3, 1), (392.0, 1), (369.99, 1),
        (349.23, 1), (329.63, 1), (311.13, 1), (293.66, 1), (277.18, 1), (293.66, 1),
        (311.13, 1), (329.63, 1), (349.23, 1), (369.99, 1), (392.0, 1), (369.99, 1),
        (349.23, 1), (329.63, 1), (311.13, 1), (329.63, 1), (349.23, 1), (369.99, 1),
        (392.0, 1), (415.3, 1), (440.0, 1), (293.66, 1), (311.13, 1), (329.63, 1),
        (311.13, 1), (293.66, 1), (277.18, 1), (293.66, 1), (311.13, 1), (329.63, 1),
        (311.13, 1), (293.66, 1), (277.18, 1), (293.66, 1), (311.13, 1), (329.63, 1),
        (311.13, 1), (293.66, 1), (277.18, 1), (293.66, 1), (311.13, 1), (329.63, 1),
        (311.13, 1), (293.66, 1), (277.18, 1), (293.66, 1), (311.13, 1), (329.63, 1),
        (349.23, 1), (369.99, 1), (349.23, 1), (329.63, 1), (311.13, 1), (293.66, 1),
        (311.13, 1), (329.63, 1), (311.13, 1), (293.66, 1), (277.18, 1), (293.66, 1),
        (311.13, 1), (329.63, 1), (311.13, 1), (293.66, 1), (277.18, 1), (293.66, 1),
        (311.13, 1), (329.63, 1), (311.13, 1), (293.66, 1), (277.18, 1), (293.66, 1),
        (311.13, 1), (329.63, 1), (311.13, 1), (293.66, 1), (277.18, 1), (293.66, 1),
        (311.13, 1), (329.63, 1), (349.23, 1), (369.99, 1), (349.23, 1), (329.63, 1),
        (277.18, 1), (293.66, 1), (311.13, 1), (329.63, 1), (349.23, 1), (369.99, 1),
        (392.0, 1), (415.3, 1), (440.0, 1), (415.3, 1), (392.0, 1), (369.99, 1), (349.23, 1),
        (329.63, 1), (311.13, 1), (293.66, 1), (277.18, 1), (293.66, 1), (311.13, 1),
        (329.63, 1), (349.23, 1), (369.99, 1), (392.0, 1), (415.3, 1), (440.0, 1), (415.3, 1),
        (392.0, 1), (369.99, 1), (349.23, 1), (329.63, 1), (311.13, 1), (293.66, 1),
        (277.18, 1), (293.66, 1), (311.13, 1), (329.63, 1), (349.23, 1), (369.99, 1),
        (392.0, 1), (415.3, 1), (440.0, 1), (415.3, 1), (392.0, 1), (369.99, 1), (349.23, 1),
        (329.63, 1), (311.13, 1), (293.66, 1), (277.18, 1), (293.66, 1), (311.13, 1),
        (329.63, 1), (349.23, 1), (369.99, 1), (392.0, 1), (369.99, 1), (349.23, 1),
        (329.63, 1), (311.13, 1), (329.63, 1), (349.23, 1), (369.99, 1), (392.0, 1),
        (415.3, 1), (293.66, 3), (0, 1), (261.63, 3), (0, 1), (293.66, 3), (0, 1),
        (349.23, 3), (0, 1), (329.63, 5), (0, 1), (293.66, 5), (0, 1), (349.23, 3), (0, 1),
        (440.0, 13), (0, 3),
        # ── Bars 25-33: Chorus B ──
        (392.0, 13), (0, 3), (293.66, 3), (0, 1), (261.63, 3), (0, 1),
        (293.66, 3), (0, 1), (349.23, 3), (0, 1), (392.0, 5), (0, 1),
        (440.0, 5), (0, 1), (493.88, 3), (0, 1), (523.25, 13), (0, 3),
        (783.99, 15), (0, 1), (261.63, 10), (0, 2), (261.63, 2), (0, 2),
        (293.66, 2), (261.63, 2), (0, 12), (277.18, 10), (0, 2), (277.18, 2),
        (0, 2), (349.23, 2), (311.13, 5), (0, 1), (277.18, 7), (0, 1),
    ]

    # ── Channel 2: Square wave — main melody (vel:92, vol=0.13, loudest) ──
    ch2 = [
        (783.99, 1), (739.99, 1), (698.46, 1), (1567.98, 1), (783.99, 1), (739.99, 1),
        (698.46, 1), (1567.98, 1), (783.99, 1), (739.99, 1), (698.46, 1), (1567.98, 1),
        (783.99, 1), (739.99, 1), (698.46, 1), (1567.98, 1), (783.99, 1), (739.99, 1),
        (698.46, 1), (1567.98, 1), (783.99, 1), (739.99, 1), (698.46, 1), (1567.98, 1),
        (783.99, 1), (739.99, 1), (698.46, 1), (1567.98, 1), (783.99, 1), (739.99, 1),
        (698.46, 1), (1567.98, 1), (783.99, 3), (0, 3), (392.0, 3), (0, 3), (392.0, 3),
        (0, 9), (392.0, 2), (0, 12), (392.0, 3), (0, 3), (392.0, 3), (0, 7), (369.99, 10),
        (392.0, 3), (0, 3), (392.0, 3), (0, 3), (392.0, 3), (0, 9), (392.0, 3), (0, 11),
        (392.0, 3), (0, 3), (392.0, 3), (0, 7), (392.0, 3), (0, 7), (392.0, 5), (0, 1),
        (369.99, 5), (0, 1), (329.63, 3), (0, 1), (392.0, 5), (0, 1), (440.0, 5), (0, 1),
        (392.0, 3), (0, 1), (830.61, 10), (0, 2), (783.99, 2), (0, 2), (830.61, 2),
        (783.99, 2), (0, 4), (1108.73, 7), (0, 1), (523.25, 5), (0, 1), (466.16, 5), (0, 1),
        (415.3, 3), (0, 1), (554.37, 5), (0, 1), (523.25, 5), (0, 1), (466.16, 3), (0, 1),
        (698.46, 5), (0, 1), (659.26, 5), (0, 1), (587.33, 3), (0, 1), (466.16, 3), (0, 1),
        (523.25, 3), (0, 1), (587.33, 3), (0, 1), (698.46, 3), (0, 1), (830.61, 31), (0, 1),
        (783.99, 31), (0, 1), (349.23, 7), (0, 1), (466.16, 7), (0, 1), (587.33, 7), (0, 1),
        (698.46, 7), (0, 1), (659.26, 16),
        # ── Bars 25-33: Chorus B ──
        (659.26, 15), (0, 1), (349.23, 7), (0, 1), (466.16, 7), (0, 1),
        (587.33, 7), (0, 1), (698.46, 7), (0, 1), (783.99, 15), (0, 1),
        (1046.5, 15), (0, 1), (659.26, 10), (0, 2), (659.26, 2), (0, 2),
        (698.46, 2), (659.26, 2), (0, 12), (698.46, 10), (0, 2), (698.46, 2),
        (0, 2), (830.61, 2), (783.99, 3), (0, 3), (698.46, 7), (0, 1),
    ]

    # ── Channel 3: Triangle wave — bass (vel:60, vol=0.09) ──
    ch3 = [
        (277.18, 1), (0, 1), (277.18, 1), (261.63, 1), (293.66, 1), (0, 1), (293.66, 1),
        (261.63, 1), (311.13, 1), (0, 1), (311.13, 1), (261.63, 1), (329.63, 1), (0, 1),
        (329.63, 1), (261.63, 1), (349.23, 1), (0, 1), (349.23, 1), (261.63, 1), (369.99, 1),
        (0, 1), (369.99, 1), (261.63, 1), (392.0, 1), (0, 1), (392.0, 1), (261.63, 1),
        (233.08, 2), (246.94, 2), (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2),
        (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2),
        (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2),
        (277.18, 2), (415.3, 2), (277.18, 3), (0, 1), (415.3, 2), (466.16, 2), (415.3, 2),
        (392.0, 2), (277.18, 2), (415.3, 2), (277.18, 3), (0, 1), (415.3, 2), (466.16, 2),
        (415.3, 2), (349.23, 2), (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2),
        (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2),
        (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2),
        (277.18, 2), (415.3, 2), (277.18, 3), (0, 1), (415.3, 2), (466.16, 2), (415.3, 2),
        (392.0, 2), (277.18, 2), (415.3, 2), (277.18, 3), (0, 1), (415.3, 2), (466.16, 2),
        (415.3, 2), (349.23, 2), (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2),
        (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2),
        (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2),
        (415.3, 11), (0, 1), (392.0, 2), (0, 2), (415.3, 2), (392.0, 2), (0, 4), (349.23, 2),
        (329.63, 2), (293.66, 2), (277.18, 2), (261.63, 2), (392.0, 2), (261.63, 2),
        (392.0, 2), (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2),
        (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2),
        (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2),
        (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2),
        (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2), (277.18, 2), (415.3, 2),
        (277.18, 2), (415.3, 2), (277.18, 2), (415.3, 2), (277.18, 2), (415.3, 2),
        (277.18, 2), (415.3, 2), (277.18, 2), (415.3, 2), (277.18, 2), (415.3, 2),
        (277.18, 2), (415.3, 2), (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2),
        (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2),
        (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2),
        (233.08, 2), (349.23, 2), (233.08, 2), (349.23, 2), (233.08, 2), (349.23, 2),
        (233.08, 2), (349.23, 2), (233.08, 2), (349.23, 2), (233.08, 2), (349.23, 2),
        (233.08, 2), (349.23, 2), (233.08, 2), (349.23, 2), (261.63, 2), (392.0, 2),
        (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2),
        # ── Bars 25-33: Chorus B ──
        (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2),
        (261.63, 2), (392.0, 2), (261.63, 2), (349.23, 2), (261.63, 2), (349.23, 2),
        (261.63, 2), (349.23, 2), (261.63, 2), (349.23, 2), (261.63, 2), (349.23, 2),
        (261.63, 2), (349.23, 2), (261.63, 2), (349.23, 2), (261.63, 2), (349.23, 2),
        (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2),
        (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2),
        (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2),
        (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2),
        (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2), (261.63, 2), (392.0, 2),
        (261.63, 2), (392.0, 2), (277.18, 2), (415.3, 2), (277.18, 2), (415.3, 2),
        (277.18, 2), (415.3, 2), (277.18, 2), (415.3, 2), (277.18, 2), (415.3, 2),
        (277.18, 2), (415.3, 2), (277.18, 2), (415.3, 2), (277.18, 2), (415.3, 2),
    ]

    # ── Render Channel 1: square, vol=0.10 ──
    ch1_samples = []
    for freq, dur16 in ch1:
        dur_sec = dur16 * sixteenth
        n = _note(freq, dur_sec * 0.92, wave='square', vol=0.10,
                  attack=0.003, decay=0.01, sustain=0.6, release=0.008)
        for _ in range(dur16):
            ch1_samples.extend(_pad16(n[:sixteenth_samp]))
            n = n[sixteenth_samp:]  # advance through the note

    # ── Render Channel 2: square, vol=0.13 ──
    ch2_samples = []
    for freq, dur16 in ch2:
        dur_sec = dur16 * sixteenth
        n = _note(freq, dur_sec * 0.92, wave='square', vol=0.13,
                  attack=0.003, decay=0.02, sustain=0.65, release=0.01)
        for _ in range(dur16):
            ch2_samples.extend(_pad16(n[:sixteenth_samp]))
            n = n[sixteenth_samp:]

    # ── Render Channel 3: triangle, vol=0.09 ──
    ch3_samples = []
    for freq, dur16 in ch3:
        dur_sec = dur16 * sixteenth
        n = _note(freq, dur_sec * 0.92, wave='triangle', vol=0.09,
                  attack=0.005, decay=0.02, sustain=0.6, release=0.015)
        for _ in range(dur16):
            ch3_samples.extend(_pad16(n[:sixteenth_samp]))
            n = n[sixteenth_samp:]

    # ── Channel 4: Noise drum pattern (Game Boy noise channel) ──
    ch4_samples = []
    for bar in range(n_bars):
        for pos in range(16):
            hit = [0] * sixteenth_samp
            # Hi-hat on every 8th note (even positions)
            if pos % 2 == 0:
                hh = _envelope(_noise(sixteenth * 0.3, 0.04),
                               attack=0.001, decay=0.008, sustain_level=0.02, release=0.005)
                for i in range(min(len(hh), len(hit))):
                    hit[i] += hh[i]
            # Kick on beats 1 and 3 (pos 0, 8)
            if pos in (0, 8):
                kick_tone = _envelope(_sine(80, sixteenth * 0.5, 0.08),
                                      attack=0.001, decay=0.03, sustain_level=0.1, release=0.02)
                kick_noise = _envelope(_noise(0.015, 0.06),
                                       attack=0.001, decay=0.005, sustain_level=0.01, release=0.003)
                kick = _mix(kick_tone, kick_noise)
                for i in range(min(len(kick), len(hit))):
                    hit[i] += kick[i]
            # Snare on beats 2 and 4 (pos 4, 12)
            if pos in (4, 12):
                snare_tone = _envelope(_sine(200, sixteenth * 0.3, 0.05),
                                       attack=0.001, decay=0.01, sustain_level=0.05, release=0.008)
                snare_noise = _envelope(_noise(sixteenth * 0.4, 0.06),
                                        attack=0.001, decay=0.015, sustain_level=0.03, release=0.01)
                snare = _mix(snare_tone, snare_noise)
                for i in range(min(len(snare), len(hit))):
                    hit[i] += snare[i]
            ch4_samples.extend(_pad16(hit))

    # ── Mix all 4 channels ──
    for arr in (ch1_samples, ch2_samples, ch3_samples, ch4_samples):
        while len(arr) < total_samp:
            arr.append(0)

    samples = _mix_layers(
        ch1_samples[:total_samp],
        ch2_samples[:total_samp],
        ch3_samples[:total_samp],
        ch4_samples[:total_samp],
    )

    # Soft clip to avoid harsh distortion
    peak = max(abs(s) for s in samples) if samples else 1
    if peak > 32767:
        scale = 32767 / peak
        samples = [s * scale for s in samples]

    # Split: bars 0-1 (chromatic intro) → SFX, bars 2-33 (loop body) → BGM
    _write("sfx_encounter_pkmn.wav", samples[:intro_samp])
    _write("bgm_battle_pkmn.wav", samples[intro_samp:total_samp])


# ── Main ──────────────────────────────────────────────────────────────

def generate_all():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    print("Generating sound assets...")
    gen_step()
    gen_select()
    gen_encounter()
    gen_hit()
    gen_attack()
    gen_heal()
    gen_text()
    gen_spare()
    gen_save()
    gen_item()
    gen_levelup()
    gen_ominous()
    # Monster-specific SFX
    gen_atk_cursor()
    gen_atk_ping()
    gen_atk_blob()
    gen_atk_null()
    gen_atk_daemon()
    gen_blt_cursor()
    gen_blt_ping()
    gen_blt_blob()
    gen_blt_null()
    gen_blt_daemon()
    gen_atk_pkmn()
    gen_blt_pkmn()
    gen_cry_pkmn()
    gen_critical()
    gen_whiff()
    # v1.3 SFX
    gen_streak()
    gen_seq_step()
    gen_seq_reject()
    gen_seq_solve()
    gen_death()
    gen_menu_open()
    # BGMs
    gen_bgm_title()
    gen_bgm_overworld()
    gen_bgm_battle()
    gen_bgm_battle_cursor()
    gen_bgm_battle_ping()
    gen_bgm_battle_blob()
    gen_bgm_battle_null()
    gen_bgm_battle_daemon()
    gen_bgm_battle_pkmn()
    print(f"Done! Assets written to {ASSETS_DIR}/")


if __name__ == "__main__":
    generate_all()
