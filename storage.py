"""
storage.py — local persistence for Livestock Farm Assistant.
All data lives in ~/.farm_assistant/data.json.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, date
from pathlib import Path
from typing import Any

# ── paths ──────────────────────────────────────────────────────────────────
DATA_DIR = Path.home() / ".farm_assistant"
DATA_FILE = DATA_DIR / "data.json"


def _load() -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"animals": [], "log": []}


def _save(data: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ── animals ────────────────────────────────────────────────────────────────

def list_animals() -> list[dict]:
    return _load()["animals"]


def get_animal(animal_id: str) -> dict | None:
    for a in list_animals():
        if a["id"] == animal_id:
            return a
    return None


def add_animal(name: str, species: str, breed: str, dob: str, notes: str) -> dict:
    data = _load()
    animal = {
        "id": str(uuid.uuid4()),
        "name": name.strip(),
        "species": species.strip(),
        "breed": breed.strip(),
        "dob": dob.strip(),
        "notes": notes.strip(),
        "created_at": datetime.now().isoformat(),
    }
    data["animals"].append(animal)
    _save(data)
    return animal


def update_animal(animal_id: str, **fields) -> bool:
    data = _load()
    for a in data["animals"]:
        if a["id"] == animal_id:
            for k, v in fields.items():
                if k in ("name", "species", "breed", "dob", "notes"):
                    a[k] = v.strip() if isinstance(v, str) else v
            a["updated_at"] = datetime.now().isoformat()
            _save(data)
            return True
    return False


def delete_animal(animal_id: str) -> bool:
    data = _load()
    before = len(data["animals"])
    data["animals"] = [a for a in data["animals"] if a["id"] != animal_id]
    if len(data["animals"]) < before:
        _save(data)
        return True
    return False


# ── farm log ───────────────────────────────────────────────────────────────

def list_log(limit: int = 200) -> list[dict]:
    entries = _load()["log"]
    return sorted(entries, key=lambda e: e["date"], reverse=True)[:limit]


def add_log_entry(
    entry_date: str,
    category: str,
    notes: str,
    animal_id: str | None = None,
) -> dict:
    data = _load()
    entry = {
        "id": str(uuid.uuid4()),
        "date": entry_date,
        "category": category,
        "notes": notes.strip(),
        "animal_id": animal_id,
        "created_at": datetime.now().isoformat(),
    }
    data["log"].append(entry)
    _save(data)
    return entry


def delete_log_entry(entry_id: str) -> bool:
    data = _load()
    before = len(data["log"])
    data["log"] = [e for e in data["log"] if e["id"] != entry_id]
    if len(data["log"]) < before:
        _save(data)
        return True
    return False


# ── context summary for the AI ─────────────────────────────────────────────

def recent_context_summary(max_entries: int = 15) -> str:
    """
    Build a plain-text context block prepended to every AI prompt.
    Includes the animal registry and the most recent log entries.

    Keep max_entries low (default 15) on 8 GB RAM machines — each entry
    adds tokens that grow the KV cache.  Raise it only if you have 16 GB+.
    The whole block should stay under ~600 tokens to leave room for the
    model's reply within the num_ctx=2048 budget.
    """
    animals = list_animals()
    log = list_log(limit=max_entries)

    lines: list[str] = []

    # ── animal registry ──
    if animals:
        lines.append("=== ANIMAL REGISTRY ===")
        for a in animals:
            parts = [f"{a['name']} ({a['species']}"]
            if a.get("breed"):
                parts[0] += f", {a['breed']}"
            parts[0] += ")"
            if a.get("dob"):
                parts.append(f"DOB: {a['dob']}")
            if a.get("notes"):
                parts.append(f"Notes: {a['notes']}")
            lines.append(" | ".join(parts))
    else:
        lines.append("=== ANIMAL REGISTRY ===\n(no animals registered yet)")

    lines.append("")

    # ── recent log ──
    if log:
        lines.append(f"=== RECENT FARM LOG (last {len(log)} entries) ===")
        for e in log:
            animal_label = ""
            if e.get("animal_id"):
                a = get_animal(e["animal_id"])
                if a:
                    animal_label = f" [{a['name']}]"
            lines.append(f"{e['date']} | {e['category']}{animal_label}: {e['notes']}")
    else:
        lines.append("=== RECENT FARM LOG ===\n(no entries yet)")

    return "\n".join(lines)
