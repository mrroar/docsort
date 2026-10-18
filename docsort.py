#!/usr/bin/env python3
"""
docsort – ein Mini-Harness zur Dokumentenklassifizierung (macOS, Ollama).

Lernprojekt: Tools, Skills, Knowledge, Guardrails, State und Logging
in Miniaturform – bewusst ohne Framework.

Projektlayout (das Skript legt fehlende Dateien beim ersten Start selbst an):

    docsort/
    ├── docsort.py          <- dieses Skript
    ├── skills/
    │   └── classify.md     <- Skill: Anleitung, WIE klassifiziert wird
    ├── knowledge/
    │   └── categories.md   <- Knowledge: WAS die Kategorien bedeuten
    ├── logs/
    │   └── run_*.jsonl    <- State/Logging: ein Eintrag pro Dokument
    └── input/              <- hier liegen die zu sortierenden Dateien

Aufruf:
    python3 docsort.py input/ --target archiv/ [--dry-run] [--model llama3.1:8b]

Voraussetzungen:
    brew install ollama && ollama serve
    ollama pull llama3.1:8b
    pip3 install pymupdf
    (optional fuer Scans: brew install ocrmypdf)
"""

from __future__ import annotations

import argparse
import datetime
import json
import shutil
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Basiskonfiguration
# ---------------------------------------------------------------------------

OLLAMA_URL = "http://localhost:11434/api/chat"
SKILL_FILE = Path(__file__).parent / "skills" / "classify.md"
KNOWLEDGE_FILE = Path(__file__).parent / "knowledge" / "categories.md"
LOG_DIR = Path(__file__).parent / "logs"
CONFIDENCE_THRESHOLD = 0.6  # Guardrail: darunter fragt der Harness den Menschen
SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md"}
MAX_CHARS = 6000  # Kontext-Management: Dokumenttext wird hierauf gekuerzt

# ---------------------------------------------------------------------------
# 1) Tool-Registry
#    Jedes Tool ist eine Funktion + einer Beschreibung fuer das Modell.
#    (In dieser Miniatur ruft der Harness die Tools deterministisch auf.
#    Die Registry zeigt das Muster, das Frameworks fuer dich abstrahieren.)
# ---------------------------------------------------------------------------

TOOLS: dict[str, dict] = {}


def tool(name: str, description: str):
    """Dekorator: registriert eine Funktion als Harness-Tool."""
    def wrapper(fn):
        TOOLS[name] = {"fn": fn, "description": description}
        return fn
    return wrapper


@tool("read_document", "Extrahiert Text aus einer Datei (PDF, TXT, MD).")
def read_document(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        try:
            import fitz  # pymupdf
            with fitz.open(path) as doc:
                text = "\n".join(page.get_text() for page in doc)
        except ImportError:
            return "[FEHLER] pymupdf ist nicht installiert: pip3 install pymupdf"
        if not text.strip():
            return "[WARNUNG] PDF enthaelt keinen Text – vermutlich ein Scan. OCR noetig (ocrmypdf)."
        return text
    return path.read_text(encoding="utf-8", errors="replace")


@tool("ask_model", "Stellt eine Klassifikationsfrage an das lokale Ollama-Modell.")
def ask_model(prompt: str, model: str) -> dict:
    import urllib.request

    payload = json.dumps({
        "model": model,
        "stream": False,
        "format": "json",  # Guardrail: Ollama erwingt JSON-Ausgabe
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return json.loads(data["message"]["content"])  # kann ValueError werfen


@tool("move_file", "Verschiebt (dry-run: kopiert) eine Datei in den Zielordner.")
def move_file(src: Path, category: str, target_root: Path, dry_run: bool) -> Path:
    dest_dir = target_root / category
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if dry_run:
        shutil.copy2(src, dest)
    else:
        shutil.move(str(src), str(dest))
    return dest


# ---------------------------------------------------------------------------
# 2) Skills & Knowledge
#    Beide sind Markdown-Dateien – vom Code getrennt, editierbar,
#    ohne Programmierkenntnisse anpassbar. Genau das ist der Punkt.
# ---------------------------------------------------------------------------

SKILL_TEMPLATE = """# Skill: Dokument klassifizieren

Du klassifizierst ein Dokument in GENAU EINE Kategorie aus der
Kategorienliste im Knowledge-Abschnitt.

Regeln:
1. Beurteile auf Basis des Dokumentinhalts, nicht des Dateinamens.
2. Antworte NUR als JSON: {"category": "...", "confidence": 0.0-1.0,
   "summary": "ein Satz"}
3. confidence spiegelt deine Sicherheit wider. Bei Unsicherheit ehrlich
   niedrig antworten – niemals erfinden.
4. Trifft keine Kategorie zu, antworte "unsicher".
"""

KNOWLEDGE_TEMPLATE = """# Knowledge: Kategorien

- rechnung: Dokument mit Rechnungsstellung, Betrag, MwSt, Rechnungsnummer
- vertrag: Vereinbarung zwischen Parteien, Laufzeit, Unterschriften, Klauseln
- kundigung: Kuendigung eines Vertrags oder Abos durch eine Partei
- sonstiges: alles andere
- unsicher: kein eindeutiger Schluss moeglich
"""


def load_context() -> str:
    """Laedt Skill + Knowledge und baut den Systemkontext."""
    skill = SKILL_FILE.read_text(encoding="utf-8")
    knowledge = KNOWLEDGE_FILE.read_text(encoding="utf-8")
    return f"{skill}\n\n{knowledge}"


def bootstrap() -> None:
    """Legt Skill-, Knowledge- und Log-Ordner beim ersten Start an."""
    for path, template in [
        (SKILL_FILE, SKILL_TEMPLATE),
        (KNOWLEDGE_FILE, KNOWLEDGE_TEMPLATE),
    ]:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(template, encoding="utf-8")
            print(f"[bootstrap] Vorlage angelegt: {path}")
    LOG_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# 3) Execution Loop (hier: eine deterministische Pipeline pro Dokument)
#    Observe -> Think -> Act -> Verify, in Miniatur.
# ---------------------------------------------------------------------------

def classify_document(path: Path, context: str, model: str) -> dict:
    text = TOOLS["read_document"]["fn"](path)[:MAX_CHARS]
    if text.startswith(("[FEHLER", "[WARNUNG")):
        return {"category": "fehler", "confidence": 0.0, "summary": text}

    prompt = f"{context}\n\n--- DOKUMENT: {path.name} ---\n{text}"
    try:
        result = TOOLS["ask_model"]["fn"](prompt, model)
    except ValueError:
        return {"category": "unsicher", "confidence": 0.0,
                "summary": "Modell-Antwort war kein gueltiges JSON"}
    return result


def verify(result: dict) -> str | None:
    """Guardrail: Prueft die Modell-Antwort gegen die Regeln."""
    valid = {"rechnung", "vertrag", "kundigung", "sonstiges", "unsicher"}
    if result.get("category") not in valid:
        return "unsicher"
    return None


def human_in_the_loop(result: dict, path: Path, categories: list[str]) -> dict:
    """Niedrige Konfidenz -> der Mensch entscheidet (Human-in-the-Loop)."""
    print(f"\n  Unsicher bei '{path.name}': "
          f"{result.get('category')} (Konfidenz {result.get('confidence')})")
    print("  Zusammenfassung:", result.get("summary", ""))
    for i, cat in enumerate(categories, 1):
        print(f"    {i}) {cat}")
    choice = input("  Ihre Wahl (Enter = unsicher, Datei bleibt liegen): ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(categories):
        return {"category": categories[int(choice) - 1], "confidence": 1.0,
                "summary": "manuell bestaetigt", "manual": True}
    return {"category": "unsicher", "confidence": 0.0,
            "summary": "vom Menschen uebersprungen", "manual": True}


def process_all(input_dir: Path, target_root: Path, model: str,
                dry_run: bool) -> None:
    bootstrap()
    context = load_context()
    log_path = LOG_DIR / f"run_{datetime.datetime.now():%Y%m%d_%H%M%S}.jsonl"
    categories = ["rechnung", "vertrag", "kundigung", "sonstiges", "unsicher"]

    files = sorted(p for p in input_dir.iterdir()
                  if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES)
    if not files:
        print(f"Keine passenden Dateien in {input_dir} gefunden.")
        return

    print(f"{len(files)} Datei(en) – Modus: "
          f"{'DRY-RUN (kopieren)' if dry_run else 'VERSCHIEBEN'} – Modell: {model}\n")

    stats: dict[str, int] = {}
    for path in files:
        print(f"→ {path.name}")
        result = classify_document(path, context, model)

        corrected = verify(result)  # Verify-Schritt
        if corrected:
            result["category"] = corrected

        if (result.get("confidence", 0) < CONFIDENCE_THRESHOLD
                and result["category"] != "unsicher"):
            result = human_in_the_loop(result, path, categories)

        if result["category"] == "unsicher":
            print("  → unsortiert liegen gelassen")
            dest = None
        else:
            dest = TOOLS["move_file"]["fn"](path, result["category"],
                                            target_root, dry_run)
            print(f"  → {result['category']}: {dest}")

        stats[result["category"]] = stats.get(result["category"], 0) + 1
        with log_path.open("a", encoding="utf-8") as log:  # Logging/State
            log.write(json.dumps({
                "file": path.name, **result,
                "target": str(dest) if dest else None,
                "dry_run": dry_run, "model": model,
            }) + "\n")

    print("\nZusammenfassung:", ", ".join(f"{k}={v}" for k, v in stats.items()))
    print(f"Protokoll: {log_path}")


# ---------------------------------------------------------------------------
# 4) CLI-Einstieg
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Mini-Harness: Dokumente sortieren")
    parser.add_argument("input", type=Path, help="Eingangsordner")
    parser.add_argument("--target", type=Path, default=Path("archiv"),
                        help="Zielordner (Standard: archiv/)")
    parser.add_argument("--model", default="llama3.1:8b", help="Ollama-Modell")
    parser.add_argument("--dry-run", action="store_true",
                        help="Kopieren statt Verschieben (Guardrail fuer Tests)")
    args = parser.parse_args()

    if not args.input.is_dir():
        print(f"Fehler: {args.input} ist kein Verzeichnis.", file=sys.stderr)
        return 1
    process_all(args.input, args.target, args.model, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())