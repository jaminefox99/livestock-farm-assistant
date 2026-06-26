# Livestock Farm Assistant (Offline)

A native desktop app for livestock farming — 100% offline, runs on an 8 GB
laptop with no GPU, no cloud, no internet after setup.

## Tabs

- **Advisor** — chat with a local AI about husbandry, feeding, breeding,
  housing, and symptoms to watch for. It automatically includes your
  animal records and recent log entries as context, so you can say
  "Is Daisy due for anything?" and it knows who Daisy is.
- **Animals** — registry of animals (name, species, breed, DOB, notes).
- **Farm Log** — dated entries (Health, Feeding, Breeding, Weight,
  Housing, General), optionally linked to a specific animal.

All data is stored locally in `~/.farm_assistant/data.json` — nothing
leaves your machine.

## ⚠️ Important: not a vet

The Advisor gives general guidance and helps you think through symptoms,
but it is **not a veterinarian** and cannot diagnose. It's built to push
you toward calling a vet for anything urgent or serious. Treat it like
an experienced neighbor, not a medical authority.

## Prerequisites

1. Install Ollama: https://ollama.com (one-time, needs internet)
2. Pull a model (one-time, needs internet):
   ```bash
   ollama pull llama3.2:3b
   ```
3. Make sure Ollama is running:
   ```bash
   ollama serve
   ```

## Setup

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

## Customize

In `app.py`:
- `MODEL_NAME` — swap models (`qwen2.5:3b`, `phi3.5`, `qwen2.5:7b`, etc.)
- `SYSTEM_PROMPT` — adjust tone, add region-specific guidance, or focus
  it further (e.g. dairy cattle only, poultry only)
- `SPECIES` / `CATEGORIES` lists — add/remove options to match your operation

In `storage.py`:
- `recent_context_summary()` controls how much farm history gets fed to
  the model each question — increase `max_entries` if you want it to
  "remember" more log history per question (costs a bit more speed).

## Packaging as a standalone app (optional)

```bash
flet pack app.py
```
Produces a double-clickable executable — no Python install needed on
the target machine (Ollama + model still required separately).

## Notes on the offline model's limits

A 3B model is good for general advice, structuring your thinking, and
record-keeping habits — it is not a substitute for breed-specific expert
knowledge or veterinary diagnosis. If you have RAM to spare, `qwen2.5:7b`
(~4.7 GB) gives noticeably better reasoning at the cost of slower replies.
