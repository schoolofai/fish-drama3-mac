#!/usr/bin/env python3
"""Whisper-check every Drama 3 take against its script and flag the ones to re-roll.

Drama 3 sometimes drops a line, stops early, or runs on into silence. This reads out/takes.json
(written by run_tests.py), transcribes each WAV with faster-whisper, strips [directions], <tags> and
<|speaker:N|> markers from the script, and prints OK or REROLL per take.

A take is REROLL when: word error rate > --max-wer (default 0.15), or more than --max-tail seconds
of silence after the last word (default 3 s, a run-away take).

Usage:
  pip install faster-whisper
  python whisper_check.py                    # out/takes.json
  python whisper_check.py --takes out/takes.json --model small.en
"""
import argparse, json, re

import numpy as np
import soundfile as sf

from faster_whisper import WhisperModel

p = argparse.ArgumentParser()
p.add_argument("--takes", default="out/takes.json")
p.add_argument("--model", default="small.en")
p.add_argument("--max-wer", type=float, default=0.15)
p.add_argument("--max-tail", type=float, default=3.0)
a = p.parse_args()


def words(t):
    t = re.sub(r"<\|speaker:\d+\|>|\[[^\]]*\]|</?\w+>", " ", t.lower()).replace("’", "'")
    return re.sub(r"[^a-z0-9'áéíóúñü ]", " ", t).split()


def wer(ref, hyp):
    d = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        prev, d[0] = d[0], i
        for j, h in enumerate(hyp, 1):
            prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (r != h))
    return d[-1] / max(len(ref), 1)


def load16k(path):
    a, sr = sf.read(path, dtype="float32", always_2d=True)
    a = a.mean(axis=1)
    n = int(len(a) * 16000 / sr)
    return np.interp(np.linspace(0, len(a) - 1, n), np.arange(len(a)), a).astype(np.float32)


asr = WhisperModel(a.model, device="auto", compute_type="int8")
results, bad = [], 0
for t in json.load(open(a.takes)):
    segs, info = asr.transcribe(load16k(t["file"]), beam_size=5, word_timestamps=True, language="en")
    segs = list(segs)
    heard = " ".join(s.text.strip() for s in segs)
    last = max((w.end for s in segs for w in (s.words or [])), default=0.0)
    tail = round(float(info.duration - last), 1)
    w = round(wer(words(t["text"]), words(heard)), 3)
    ok = bool(w <= a.max_wer and tail <= a.max_tail)
    bad += not ok
    results.append(dict(file=t["file"], wer=w, tail_s=tail, ok=ok, heard=heard))
    print(f"{'OK    ' if ok else 'REROLL'} wer={w:<5} tail={tail:>5}s  {t['file']}", flush=True)
json.dump(results, open(a.takes.replace(".json", "_whisper.json"), "w"), indent=1)
print(f"{len(results) - bad} OK, {bad} to re-roll (run again with a new --seeds value)")
