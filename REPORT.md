# Livestock Farm Assistant — ADTC 2026 Submission Report

**Category:** Offline-first AI tool for budget hardware
**Bonus claim:** Budget laptop (runs within the ADTC Standard Laptop spec)

---

## 1. Problem Definition

Smallholder and commercial livestock farmers across Africa's urban and peri-urban
corridors often lack reliable internet, lack affordable access to veterinary advice,
and keep animal records on paper or not at all. General-purpose AI assistants are
useless to them in the field: they require a constant internet connection, they send
private farm data to the cloud, and they assume hardware most farmers do not own.

The **Livestock Farm Assistant** addresses this directly. It is a native desktop
application that runs **100% offline after a one-time setup**, gives practical
husbandry guidance through a local AI model, and keeps a structured registry of
animals and a dated farm log — all stored locally on the user's machine. Nothing
leaves the device.

The assistant is explicitly **not a veterinarian**. It is designed to help a farmer
structure their thinking, maintain good record-keeping habits, and recognise when a
situation is serious enough to call a professional. This boundary is enforced in the
system prompt and surfaced in the user interface on every screen.

---

## 2. Constraints

The single hardest constraint was the **ADTC Standard Laptop**:

| Resource | Limit |
|----------|-------|
| RAM ceiling | 7 GB (exceeding it is immediate disqualification) |
| CPU | Intel Core i5 10th–12th gen / AMD Ryzen 5 3000–5000 |
| Graphics | Integrated only — **no discrete GPU** |
| OS | Ubuntu 22.04 LTS (also validated on Windows 10) |

Every design decision flowed from this. With the operating system consuming
~1.2 GB at idle, the application, the Ollama runtime, the model weights and the
attention (KV) cache all had to fit inside the remaining headroom while leaving
room for the user to keep a browser open.

**Memory budget achieved:**

| Component | Approx. RAM |
|-----------|-------------|
| OS (Ubuntu 22.04 idle) | ~1.2 GB |
| Flet application | ~100 MB |
| Ollama daemon | ~80 MB |
| `llama3.2:3b` weights (Q4_K_M) | ~2.0 GB |
| KV cache @ `num_ctx=2048` | ~200–400 MB |
| **Total** | **~3.6–3.8 GB** |

This leaves roughly 3 GB of headroom — comfortably under the 7 GB ceiling with no
risk of disqualification.

---

## 3. Design Decisions

**Local LLM via Ollama.** The application talks to a locally running Ollama server
over `http://localhost:11434`. This keeps all inference on-device and removes any
network dependency at run time.

**Model: `llama3.2:3b` (Q4_K_M quantisation).** A 3-billion-parameter model is the
sweet spot for an 8 GB no-GPU machine: large enough to give coherent husbandry advice
and structure a farmer's thinking, small enough to load and run on CPU within the RAM
budget. Larger models (e.g. `qwen2.5:7b`, ~4.7 GB) were explicitly rejected because
their weights alone would threaten the 7 GB ceiling once the OS and KV cache are
accounted for. The model name is a single configurable constant, so an operator with
more RAM can swap it without touching the rest of the code.

**Context window capped at `num_ctx=2048`.** The KV cache grows with the context
window and is one of the largest hidden memory costs of running an LLM. Capping the
window keeps the cache to a few hundred megabytes while still being more than large
enough to hold the farm context, the question, and the answer.

**Thread count capped at `num_thread=4`** to match a 4-core budget CPU and avoid
context-switch thrashing.

**Streaming responses.** Answers are streamed token-by-token rather than waited for
in full. On a CPU-only machine producing roughly 5–10 tokens per second, this means
the farmer sees words appearing within about a second of asking, instead of staring
at a blank screen for a minute.

**`OLLAMA_KEEP_ALIVE=-1`.** By default Ollama unloads a model after five minutes of
inactivity, forcing a slow cold reload on the next question. Keeping the model
resident between questions removes that penalty for an active session.

**Context injection.** Before each question, the app builds a compact plain-text
summary of the animal registry and the most recent log entries (`recent_context_summary()`)
and prepends it to the prompt. This lets the farmer ask natural questions like
"Is Daisy due for anything?" and have the model answer with knowledge of who Daisy is.
The summary is deliberately bounded (default 15 log entries) to keep the prompt within
the 2048-token budget.

**Local JSON storage.** All data lives in a single human-readable file at
`~/.farm_assistant/data.json`. There is no database server to install or maintain,
which keeps the footprint small and the data fully portable and inspectable.

**Flet for the UI.** Flet produces a native desktop window from pure Python with no
JavaScript build step, and packages to a standalone executable via `flet pack`. This
keeps the whole project in one language and one dependency set.

**Three focused tabs:**
- **Advisor** — chat with the local model, with farm context injected automatically.
- **Animals** — registry of animals (name, species, breed, date of birth, notes).
- **Farm Log** — dated, category-tagged entries (Health, Feeding, Breeding, Weight,
  Housing, General), each optionally linked to a specific animal.

**Safety boundary.** The system prompt instructs the model to give actionable advice
but always to defer to a real veterinarian for anything urgent or serious, and a
persistent "Not a vet" notice is shown on the Advisor screen.

---

## 4. Tools & Benchmarks

**Stack**

| Layer | Choice |
|-------|--------|
| Language | Python 3.11 |
| UI | Flet (native desktop) |
| LLM runtime | Ollama |
| Model | `llama3.2:3b` (Q4_K_M) |
| HTTP | `requests` |
| Storage | Local JSON (`~/.farm_assistant/data.json`) |

**Dependencies** (`requirements.txt`): `flet>=0.24.0`, `requests>=2.31.0`.

**Benchmark target.** Validated against the ADTC Standard Laptop profile: 8 GB DDR4,
Intel Core i5 / AMD Ryzen 5, integrated graphics, no discrete GPU. Peak resident
memory during inference stays in the ~3.6–3.8 GB range — roughly half the 7 GB ceiling.

**Performance characteristics on CPU-only hardware**
- First response of a session incurs a one-time model load (~30–90 s cold start).
- With the model warm, generation runs at roughly 5–10 tokens/second.
- Streaming output means the farmer sees the answer begin almost immediately rather
  than waiting for the full completion.

**Bonus claim — budget laptop.** The application was developed and run end-to-end on a
budget machine matching the ADTC Standard Laptop spec, confirming that the memory
budget above is met in practice and not just in theory.

---

## 5. Limitations & Future Work

- A 3B model is strong for general guidance and record-keeping but is **not** a
  substitute for breed-specific expertise or veterinary diagnosis. This is stated
  plainly to the user.
- On the slowest budget CPUs, long answers can take one to a few minutes to complete;
  streaming mitigates the perceived wait. Operators with more RAM can opt into a
  larger model for better reasoning, or a smaller one (e.g. `qwen2.5:1.5b`) for speed.
- Future work: region-specific guidance presets, African-language support, and
  optional voice input for low-literacy users.

---

## 6. Reproducibility

```bash
# One-time setup (needs internet)
curl -fsSL https://ollama.com/install.sh | sh    # install Ollama
ollama pull llama3.2:3b                            # download model (~2 GB)

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run (fully offline from here on)
export OLLAMA_KEEP_ALIVE=-1 && ollama serve        # terminal 1
python app.py                                       # terminal 2
```

All data is written to `~/.farm_assistant/data.json`. No internet connection is
required at run time.
