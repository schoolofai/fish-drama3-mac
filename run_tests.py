#!/usr/bin/env python3
"""Generate Fish Audio Drama 3 takes locally on Apple Silicon (mlx-audio + mlx-community/fish-audio-drama-3-8bit).

Loads the model once, then renders every line in a JSON file for each seed, writing WAVs to out/ and
printing one JSON line per take (seconds to generate, seconds of audio, real-time factor, MLX peak memory).

Usage:
  python run_tests.py                                  # examples/lines.json, seeds 13,113,213, no reference
  python run_tests.py --lines examples/fernando.json --seeds 13
  python run_tests.py --ref inputs/ref.wav --ref-text inputs/ref.txt   # clone a voice you have consent for
"""
import argparse, json, os, time

import mlx.core as mx
import numpy as np
import soundfile as sf
from mlx_audio.tts.utils import load_model

p = argparse.ArgumentParser()
p.add_argument("--model", default="models/drama-3-8bit")
p.add_argument("--lines", default="examples/lines.json", help='JSON list of ["id", "text with [directions]"]')
p.add_argument("--seeds", default="13,113,213")
p.add_argument("--out", default="out")
p.add_argument("--ref", help="reference clip (10-30 s). Your own voice or someone who said yes.")
p.add_argument("--ref-text", help="text file with the exact transcript of --ref")
p.add_argument("--max-tokens", type=int, default=1200)
a = p.parse_args()

t0 = time.time()
model = load_model(a.model)
print(json.dumps({"event": "load", "seconds": round(time.time() - t0, 1)}), flush=True)
sr = model.sample_rate
os.makedirs(a.out, exist_ok=True)
lines = json.load(open(a.lines))
ref_text = open(a.ref_text).read().strip() if a.ref_text else None
log = []
for line_id, text in lines:
    for seed in [int(s) for s in a.seeds.split(",")]:
        out = os.path.join(a.out, f"{line_id}_s{seed}.wav")
        kw = dict(temperature=1.0, top_p=0.9, top_k=30, max_tokens=a.max_tokens)
        if a.ref:
            kw.update(ref_audio=a.ref, ref_text=ref_text)
        mx.random.seed(seed)
        t = time.time()
        chunks = [np.array(r.audio) for r in model.generate(text=text, **kw)]
        audio = np.concatenate(chunks) if chunks else np.zeros(1, np.float32)
        sf.write(out, audio, sr)
        gen_s, audio_s = time.time() - t, len(audio) / sr
        row = dict(file=out, id=line_id, seed=seed, text=text, gen_s=round(gen_s, 1), audio_s=round(audio_s, 2),
                   rtf=round(gen_s / max(audio_s, 1e-6), 2), peak_gb=round(mx.get_peak_memory() / 1e9, 1))
        print(json.dumps(row), flush=True)
        log.append(row)
json.dump(log, open(os.path.join(a.out, "takes.json"), "w"), indent=1)
print(json.dumps({"event": "done", "takes": len(log)}), flush=True)
