# fish-drama3-mac

**Video:** VIDEO_URL_TBD ("Fish Audio Drama 3: Can You Tell Which Is ElevenLabs? (Free, on a Mac)", ProAI Clips)

Run **Fish Audio Drama 3** locally on an Apple Silicon Mac with [mlx-audio](https://github.com/Blaizzy/mlx-audio) and the community 8-bit MLX conversion [`mlx-community/fish-audio-drama-3-8bit`](https://huggingface.co/mlx-community/fish-audio-drama-3-8bit). Every tag from the video's 13-beat showcase is in [`examples/lines.json`](examples/lines.json).

> **Honesty note:** this is a **community conversion**, not an official Fish Audio release. Fish lists the official Drama 3 model as NVIDIA-only with 48 GB+ GPU memory ([install docs](https://speech.fish.audio/install/)). Built with Fish Audio.

## Requirements
- Apple Silicon Mac. **128 GB unified memory recommended**; 64 GB is tight; less is not enough for this route. Tested on M4 Max, 128 GB, macOS 15.
- About 45 GB free disk (42 GB model + ~1 GB Python packages).
- [uv](https://docs.astral.sh/uv/) and Python 3.12 (uv installs it for you).

## Quick start
Each step lists what it does, the exact command, what you should see, and where it is in the video.

### 1. Make a working folder
- **What:** one folder for the model, inputs and outputs.
- **Command:**
  ```bash
  mkdir -p ~/fish-drama3-mac/{inputs,out,models} && cd ~/fish-drama3-mac
  git clone https://github.com/schoolofai/fish-drama3-mac repo && cp repo/*.py . && cp -r repo/examples .
  ```
- **Expect:** no errors; `ls` shows `examples  inputs  models  out  run_tests.py  whisper_check.py`.
- **Video:** 6:54

### 2. Create a Python 3.12 environment
- **What:** an isolated environment so nothing touches your system Python.
- **Command:**
  ```bash
  uv venv .venv --python 3.12 && . .venv/bin/activate
  ```
- **Expect:** `Creating virtual environment at: .venv`, then `(.venv)` at the start of your prompt.
- **Video:** 6:54

### 3. Install mlx-audio from its main branch
- **What:** Drama 3 support (`fish_drama3`) is merged into mlx-audio's `main` branch but not yet in a release, so install from GitHub.
- **Command:**
  ```bash
  uv pip install "mlx-audio @ git+https://github.com/Blaizzy/mlx-audio" "huggingface_hub[cli]" soundfile faster-whisper
  ```
- **Expect:** `Installed N packages` at the end (about 1 GB). No cmake needed.
- **Video:** 7:01

### 4. Download the 8-bit MLX model (42 GB)
- **What:** the community conversion. Routed experts are 8-bit (from Fish's FP8 release); everything else stays bf16.
- **Command:**
  ```bash
  hf download mlx-community/fish-audio-drama-3-8bit --local-dir models/drama-3-8bit
  ```
- **Expect:** a progress bar, then about 42 GB in `models/drama-3-8bit` (about 25 minutes at ~25 MB/s).
- **Video:** 7:10

### 5. Generate the showcase lines
- **What:** loads the model once (about 10 s warm, ~23 s the first time), then renders every line in `examples/lines.json` for seeds 13, 113 and 213. All character lines use one voice setting, "Voice 3": **no reference clip**, direction `[warm, theatrical, strong Spanish accent]`.
- **Command:**
  ```bash
  /usr/bin/time -l python run_tests.py --lines examples/lines.json --seeds 13,113,213
  python run_tests.py --lines examples/fernando.json --seeds 13,113,213 --out out/fernando
  ```
- **Expect:** a line like `{"event": "load", "seconds": 10.5}`, then one JSON line per take with `gen_s`, `audio_s`, `rtf` (1.2-1.9 on an M4 Max, i.e. slower than real time) and `peak_gb` (about 50-56). WAVs land in `out/`, plus `out/takes.json`. `/usr/bin/time -l` prints the whole-process `peak memory footprint` at the end (we saw 98.6 GB).
- **Video:** 7:16 (showcase from 1:19, Uncle Fernando at 5:38)

### 6. Whisper-check every take and re-roll failures
- **What:** Drama 3 sometimes drops a sentence, stops early or runs on into silence (about 1 in 3 directed takes for us; the crying line failed every time). This transcribes each take and flags it.
- **Command:**
  ```bash
  python whisper_check.py --takes out/takes.json
  python whisper_check.py --takes out/fernando/takes.json
  ```
- **Expect:** one line per take, `OK` or `REROLL` with its word error rate and trailing silence, then e.g. `41 OK, 13 to re-roll`. Re-run step 5 with new `--seeds` for the REROLL lines.
- **Video:** 8:03

### 7. (Optional) Clone your own voice
- **What:** record 10-30 s of **your own** voice (or someone who has said yes) in a quiet room, save it as `inputs/ref.wav`, and its exact transcript as `inputs/ref.txt`.
- **Command:**
  ```bash
  python run_tests.py --ref inputs/ref.wav --ref-text inputs/ref.txt --lines examples/lines.json --seeds 13
  ```
- **Expect:** the same lines, now in the reference voice. Cloning a real person without consent is banned by the licence.
- **Video:** 6:13

## Tag cheat sheet (from the video)
| Syntax | Example | Our result |
|---|---|---|
| free-form direction | `[whispering]`, `[shouting, across a noisy room]`, `[sighs]`, `[laughs]` | worked |
| mid-line change | `... [voice drops to a whisper] ... [slow, deadly serious] ...` | worked |
| paired tags | `<emphasis>`, `<whisper>`, `<fast>`, `<slow>`, `<soft>`, `<stress>`, `<forceful>` | worked |
| `[pause]` | `The winner is... [pause] still stuck in traffic.` | worked |
| two speakers | `<\|speaker:0\|> ... <\|speaker:1\|> ...` | worked |
| English to Spanish switch / Spanish direction | `Bienvenidos de nuevo...` | partial (coin flip) |
| crying | `[choked up, crying quietly] ... [voice breaking] ...` | failed (2nd sentence dropped) |

Video timestamp for the syntax: 0:46.

## Files
- `run_tests.py`: load once, render lines x seeds, log RTF and memory (temperature 1.0, top_p 0.9, top_k 30).
- `whisper_check.py`: faster-whisper read-back, WER + trailing-silence check, OK/REROLL.
- `examples/lines.json`: the showcase lines with Voice 3 direction. `examples/fernando.json`: Uncle Fernando (original character).

## Troubleshooting
- **Take goes silent or drops a line:** re-roll with a new seed (`--seeds 313`). Keep `--max-tokens` modest so run-away takes stop early.
- **Memory pressure / swap:** close other apps. 64 GB Macs are tight; the whole-process footprint reached 98.6 GB here.
- **`fish_drama3` not found:** you installed a mlx-audio release; reinstall from the GitHub `main` branch (step 3).

## Licence
- Code in this repo: MIT (see `LICENSE`). The model is **not** included.
- Model: [Fish Audio Community License v1.0](https://huggingface.co/fishaudio/drama-3) (the MLX conversion carries the same licence). Free commercial use under US$500K annual revenue; a separate licence above that or to offer TTS/cloning as a service. No cloning a real person's voice without consent, no removing watermarks, no training other speech models on outputs. Credit: **Built with Fish Audio**.
- Demo voices in the video were generated with Fish Audio Drama 3 with no voice cloning of real people; narration is an ElevenLabs synthetic voice.
