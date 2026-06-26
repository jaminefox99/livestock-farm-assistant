"""
app.py — Livestock Farm Assistant
Offline desktop app: Flet UI + Ollama (local LLM) + local JSON storage.
Compatible with Flet 0.85.x

Quickstart:
    ollama serve                   # in another terminal
    python app.py
"""

from __future__ import annotations
import json as _json
import threading
from datetime import date

import flet as ft
import requests

import storage


def safe_update(ctrl):
    """Call .update() but ignore errors when the control isn't on the page yet."""
    try:
        ctrl.update()
    except Exception:
        pass


# ── config ──────────────────────────────────────────────────────────────────
MODEL_NAME = "llama3.2:3b"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_OPTIONS = {"num_ctx": 2048, "num_thread": 4}

SYSTEM_PROMPT = """You are a practical livestock farming assistant with broad knowledge of
animal husbandry, feeding, breeding, housing, and common health issues.

Rules you always follow:
- Give clear, actionable advice a working farmer can act on today.
- When symptoms are described, help the farmer think through possibilities, but
  always remind them you are NOT a veterinarian and anything serious or urgent
  needs a real vet.
- Use the farm context provided — refer to animals by name when relevant.
- Keep answers concise. Use bullet points for lists.
- If you don't know something, say so rather than guessing."""

SPECIES = [
    "Cattle", "Goat", "Sheep", "Pig", "Poultry (Chicken)",
    "Poultry (Turkey)", "Poultry (Duck)", "Rabbit", "Horse", "Donkey", "Other",
]
CATEGORIES = ["Health", "Feeding", "Breeding", "Weight", "Housing", "General"]

# ── colours ──────────────────────────────────────────────────────────────────
BG      = "#1C1A17"
SURFACE = "#26231E"
CARD    = "#312D27"
BORDER  = "#4A4540"
ACCENT  = "#8DB87A"
ACCENT2 = "#C8974A"
TEXT    = "#EDE8DF"
SUBTEXT = "#A09890"
ERROR   = "#E07070"
USER_BG = "#2E3B2A"
AI_BG   = "#2D2920"

CATEGORY_COLORS = {
    "Health": "#E07070", "Feeding": "#8DB87A", "Breeding": "#C8974A",
    "Weight": "#7AB8B8", "Housing": "#A07AB8", "General": "#A09890",
}


# ── helpers ──────────────────────────────────────────────────────────────────

def field(label, **kwargs):
    return ft.TextField(
        label=label,
        bgcolor=CARD, border_color=BORDER, focused_border_color=ACCENT,
        color=TEXT, label_style=ft.TextStyle(color=SUBTEXT),
        **kwargs,
    )


def pad(l=0, t=0, r=0, b=0):
    return ft.Padding(left=l, top=t, right=r, bottom=b)


def card(content):
    return ft.Container(
        content=content, bgcolor=CARD, border_radius=10,
        padding=pad(14, 10, 14, 10), border=ft.Border.all(1, BORDER),
    )


def section(content):
    return ft.Container(
        content=content, bgcolor=SURFACE, border_radius=10,
        padding=pad(16, 16, 16, 16), border=ft.Border.all(1, BORDER),
    )


# ─────────────────────────────────────────────────────────────────────────────
#  ADVISOR TAB
# ─────────────────────────────────────────────────────────────────────────────

def build_advisor(page):
    chat_col = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)

    def bubble(text, is_user):
        return ft.Container(
            content=ft.Text(text, color=TEXT, size=14, selectable=True),
            bgcolor=USER_BG if is_user else AI_BG,
            border_radius=ft.BorderRadius(
                top_left=12, top_right=12,
                bottom_left=0 if is_user else 12,
                bottom_right=12 if is_user else 0,
            ),
            padding=pad(14, 10, 14, 10),
            margin=ft.Margin(left=60 if is_user else 0, top=0,
                             right=0 if is_user else 60, bottom=0),
        )

    thinking = ft.Container(
        content=ft.Row([
            ft.ProgressRing(width=16, height=16, stroke_width=2, color=ACCENT),
            ft.Text("Thinking…", color=SUBTEXT, size=13, italic=True),
        ], spacing=8),
        visible=False, margin=ft.Margin(left=0, top=4, right=0, bottom=0),
    )

    user_input = ft.TextField(
        hint_text="Ask anything about your animals…",
        hint_style=ft.TextStyle(color=SUBTEXT),
        multiline=True, min_lines=1, max_lines=5, expand=True,
        bgcolor=CARD, border_color=BORDER, focused_border_color=ACCENT,
        color=TEXT, cursor_color=ACCENT, text_size=14, border_radius=10,
    )

    def send(e=None):
        question = (user_input.value or "").strip()
        if not question:
            return
        user_input.value = ""
        safe_update(user_input)
        chat_col.controls.append(bubble(question, is_user=True))
        thinking.visible = True
        safe_update(chat_col)
        safe_update(thinking)

        def call_ollama():
            ctx = storage.recent_context_summary()
            prompt = f"{ctx}\n\n---\n\nFarmer's question: {question}"
            try:
                resp = requests.post(
                    OLLAMA_URL,
                    json={"model": MODEL_NAME, "prompt": prompt,
                          "system": SYSTEM_PROMPT, "stream": True,
                          "options": OLLAMA_OPTIONS},
                    timeout=120, stream=True,
                )
                resp.raise_for_status()
                stream_text = ft.Text("", color=TEXT, size=14, selectable=True)
                stream_bubble = ft.Container(
                    content=stream_text, bgcolor=AI_BG,
                    border_radius=ft.BorderRadius(top_left=12, top_right=12, bottom_left=12, bottom_right=0),
                    padding=pad(14, 10, 14, 10),
                    margin=ft.Margin(left=0, top=0, right=60, bottom=0),
                )
                thinking.visible = False
                chat_col.controls.append(stream_bubble)
                safe_update(chat_col)
                safe_update(thinking)
                accumulated = ""
                for raw in resp.iter_lines():
                    if not raw:
                        continue
                    try:
                        chunk = _json.loads(raw)
                    except ValueError:
                        continue
                    accumulated += chunk.get("response", "")
                    stream_text.value = accumulated
                    safe_update(stream_text)
                    if chunk.get("done"):
                        break
                try:
                    chat_col.scroll_to(offset=-1, duration=300)
                except Exception:
                    pass
            except requests.exceptions.ConnectionError:
                thinking.visible = False
                chat_col.controls.append(bubble(
                    "⚠️  Cannot reach Ollama.\n\nMake sure it's running:\n    ollama serve\n\nThen try again.",
                    is_user=False))
                safe_update(chat_col)
                safe_update(thinking)
            except Exception as ex:
                thinking.visible = False
                chat_col.controls.append(bubble(f"⚠️  Error: {ex}", is_user=False))
                safe_update(chat_col)
                safe_update(thinking)

        threading.Thread(target=call_ollama, daemon=True).start()

    user_input.on_submit = send

    return ft.Column([
        ft.Container(content=chat_col, expand=True, border=ft.Border.all(1, BORDER),
                     border_radius=10, padding=12, bgcolor=SURFACE),
        thinking,
        ft.Container(
            content=ft.Text("ℹ️  Not a vet. For anything serious or urgent, call a professional.",
                            color=ACCENT2, size=12, italic=True),
            padding=pad(4, 6, 4, 6)),
        ft.Row([user_input,
                ft.IconButton(icon=ft.Icons.SEND_ROUNDED, icon_color=ACCENT,
                              icon_size=22, tooltip="Send", on_click=send)],
               vertical_alignment=ft.CrossAxisAlignment.END, spacing=8),
    ], expand=True, spacing=8)


# ─────────────────────────────────────────────────────────────────────────────
#  ANIMALS TAB
# ─────────────────────────────────────────────────────────────────────────────

def build_animals(page):
    list_col  = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=8)
    f_name    = field("Name")
    f_species = ft.Dropdown(label="Species",
        options=[ft.dropdown.Option(s) for s in SPECIES],
        bgcolor=CARD, border_color=BORDER, focused_border_color=ACCENT,
        color=TEXT, label_style=ft.TextStyle(color=SUBTEXT))
    f_breed = field("Breed (optional)")
    f_dob   = field("Date of birth (YYYY-MM-DD, optional)")
    f_notes = field("Notes", multiline=True, min_lines=2, max_lines=4)
    err     = ft.Text("", color=ERROR, size=12)
    edit_id = [None]

    def clear():
        f_name.value = f_breed.value = f_dob.value = f_notes.value = ""
        f_species.value = None
        err.value = ""
        edit_id[0] = None
        for c in [f_name, f_species, f_breed, f_dob, f_notes, err]:
            safe_update(c)

    def refresh():
        list_col.controls.clear()
        for a in sorted(storage.list_animals(), key=lambda x: x["name"].lower()):
            def make_edit(an):
                def _e(e):
                    edit_id[0] = an["id"]
                    f_name.value    = an["name"]
                    f_species.value = an["species"]
                    f_breed.value   = an.get("breed", "")
                    f_dob.value     = an.get("dob", "")
                    f_notes.value   = an.get("notes", "")
                    err.value = ""
                    for c in [f_name, f_species, f_breed, f_dob, f_notes, err]:
                        safe_update(c)
                return _e

            def make_del(aid):
                def _d(e):
                    storage.delete_animal(aid)
                    refresh()
                return _d

            tag = ft.Container(
                content=ft.Text(a["species"], size=11, color=BG, weight=ft.FontWeight.W_600),
                bgcolor=ACCENT2, border_radius=6, padding=pad(6, 2, 6, 2))
            sub = (f"{a.get('breed','')}  " + (f"Born {a['dob']}" if a.get('dob') else "")).strip()
            sub = sub or "No extra details"
            list_col.controls.append(card(ft.Row([
                ft.Column([
                    ft.Row([ft.Text(a["name"], color=TEXT, size=15, weight=ft.FontWeight.W_600), tag], spacing=8),
                    ft.Text(sub, color=SUBTEXT, size=12),
                    ft.Text(a.get("notes",""), color=SUBTEXT, size=12, italic=True) if a.get("notes") else ft.Container(),
                ], expand=True, spacing=3),
                ft.Row([
                    ft.IconButton(icon=ft.Icons.EDIT_OUTLINED, icon_color=ACCENT, icon_size=18, on_click=make_edit(a)),
                    ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color=ERROR, icon_size=18, on_click=make_del(a["id"])),
                ], spacing=0),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.START)))
        if not list_col.controls:
            list_col.controls.append(ft.Container(
                content=ft.Text("No animals yet — add one below.", color=SUBTEXT, size=14, italic=True),
                padding=pad(20, 20, 20, 20)))
        safe_update(list_col)

    def save(e):
        name = (f_name.value or "").strip()
        sp   = f_species.value or ""
        if not name:
            err.value = "Name is required."; safe_update(err); return
        if not sp:
            err.value = "Species is required."; safe_update(err); return
        err.value = ""
        if edit_id[0]:
            storage.update_animal(edit_id[0], name=name, species=sp,
                breed=f_breed.value or "", dob=f_dob.value or "", notes=f_notes.value or "")
        else:
            storage.add_animal(name=name, species=sp,
                breed=f_breed.value or "", dob=f_dob.value or "", notes=f_notes.value or "")
        clear(); refresh()

    refresh()
    return ft.Column([
        ft.Container(content=list_col, expand=True),
        section(ft.Column([
            ft.Text("Add / Edit Animal", color=TEXT, size=15, weight=ft.FontWeight.W_600),
            ft.Row([f_name, f_species], spacing=10),
            ft.Row([f_breed, f_dob], spacing=10),
            f_notes, err,
            ft.Row([
                ft.ElevatedButton("Save animal", bgcolor=ACCENT, color=BG,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)), on_click=save),
                ft.TextButton("Clear", style=ft.ButtonStyle(color=SUBTEXT), on_click=lambda e: clear()),
            ], spacing=10),
        ], spacing=10)),
    ], expand=True, spacing=10)


# ─────────────────────────────────────────────────────────────────────────────
#  FARM LOG TAB
# ─────────────────────────────────────────────────────────────────────────────

def build_log(page):
    list_col = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=8)
    f_date   = field("Date", value=date.today().isoformat(), width=160)
    f_cat    = ft.Dropdown(label="Category", value="General",
        options=[ft.dropdown.Option(c) for c in CATEGORIES],
        bgcolor=CARD, border_color=BORDER, focused_border_color=ACCENT,
        color=TEXT, label_style=ft.TextStyle(color=SUBTEXT), width=160)
    f_animal = ft.Dropdown(label="Animal (optional)",
        bgcolor=CARD, border_color=BORDER, focused_border_color=ACCENT,
        color=TEXT, label_style=ft.TextStyle(color=SUBTEXT), expand=True)
    f_notes = field("Notes", multiline=True, min_lines=2, max_lines=5)
    err     = ft.Text("", color=ERROR, size=12)

    def refresh():
        animals = {a["id"]: a for a in storage.list_animals()}
        f_animal.options = [ft.dropdown.Option(key="", text="— none —")] + [
            ft.dropdown.Option(key=a["id"], text=a["name"])
            for a in sorted(animals.values(), key=lambda x: x["name"])]
        f_animal.value = ""
        safe_update(f_animal)

        list_col.controls.clear()
        for entry in storage.list_log():
            cat = entry.get("category", "General")
            cat_color = CATEGORY_COLORS.get(cat, SUBTEXT)
            an_label = ""
            if entry.get("animal_id") and entry["animal_id"] in animals:
                an_label = f"  ·  {animals[entry['animal_id']]['name']}"

            def make_del(eid):
                def _d(e):
                    storage.delete_log_entry(eid)
                    refresh()
                return _d

            list_col.controls.append(card(ft.Row([
                ft.Column([
                    ft.Row([
                        ft.Text(entry["date"], color=SUBTEXT, size=12),
                        ft.Container(content=ft.Text(cat, size=11, color=BG, weight=ft.FontWeight.W_600),
                                     bgcolor=cat_color, border_radius=6, padding=pad(6, 2, 6, 2)),
                        ft.Text(an_label, color=ACCENT2, size=12) if an_label else ft.Container(),
                    ], spacing=8),
                    ft.Text(entry["notes"], color=TEXT, size=13),
                ], expand=True, spacing=4),
                ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color=ERROR,
                              icon_size=16, on_click=make_del(entry["id"])),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.START)))
        if not list_col.controls:
            list_col.controls.append(ft.Container(
                content=ft.Text("No log entries yet — add one below.", color=SUBTEXT, size=14, italic=True),
                padding=pad(20, 20, 20, 20)))
        safe_update(list_col)

    def save(e):
        notes = (f_notes.value or "").strip()
        d = (f_date.value or "").strip()
        if not d:
            err.value = "Date is required."; safe_update(err); return
        if not notes:
            err.value = "Notes are required."; safe_update(err); return
        err.value = ""
        storage.add_log_entry(d, f_cat.value or "General", notes, f_animal.value or None)
        f_notes.value = ""
        f_date.value = date.today().isoformat()
        safe_update(f_notes); safe_update(f_date)
        refresh()

    refresh()
    return ft.Column([
        ft.Container(content=list_col, expand=True),
        section(ft.Column([
            ft.Text("New Log Entry", color=TEXT, size=15, weight=ft.FontWeight.W_600),
            ft.Row([f_date, f_cat, f_animal], spacing=10),
            f_notes, err,
            ft.ElevatedButton("Save entry", bgcolor=ACCENT, color=BG,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)), on_click=save),
        ], spacing=10)),
    ], expand=True, spacing=10)


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main(page: ft.Page):
    page.title = "Livestock Farm Assistant"
    page.bgcolor = BG
    page.padding = 0

    header = ft.Container(
        content=ft.Row([
            ft.Text("🌿", size=22),
            ft.Text("Farm Assistant", color=TEXT, size=18, weight=ft.FontWeight.W_700),
            ft.Container(expand=True),
            ft.Text(f"Model: {MODEL_NAME}", color=SUBTEXT, size=11),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor=SURFACE, padding=pad(20, 12, 20, 12),
        border=ft.Border(bottom=ft.BorderSide(1, BORDER)))

    bodies = [None, None, None]
    builders = [build_advisor, build_animals, build_log]
    body_container = ft.Container(expand=True)

    def show_tab(idx):
        if bodies[idx] is None:
            bodies[idx] = builders[idx](page)
        body_container.content = bodies[idx]
        safe_update(body_container)

    def on_nav(e):
        show_tab(e.control.selected_index)

    nav = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.CHAT_BUBBLE_OUTLINE_ROUNDED, label="Advisor"),
            ft.NavigationBarDestination(icon=ft.Icons.PETS_ROUNDED, label="Animals"),
            ft.NavigationBarDestination(icon=ft.Icons.BOOK_OUTLINED, label="Farm Log"),
        ],
        selected_index=0, bgcolor=SURFACE, indicator_color=ACCENT, on_change=on_nav)

    # build first tab BEFORE adding to page (no updates happen, just construction)
    bodies[0] = build_advisor(page)
    body_container.content = bodies[0]

    page.add(ft.Column([
        header,
        ft.Container(content=body_container, expand=True, padding=pad(16, 16, 16, 8)),
        nav,
    ], expand=True, spacing=0))


if __name__ == "__main__":
    ft.app(target=main)
