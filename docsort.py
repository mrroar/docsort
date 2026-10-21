#!/usr/bin/env python3
"""
docsort – ein Mini-Harness zur Dokumentenklassifizierung (macOS, Ollama).

Lernprojekt: Tools, Skills, Knowledge, Guardrails, State und Logging
in Miniaturform – bewusst ohne Framework.

Routing-Wissensbasis: knowledge/categories.md (Taxonomie v3).
Lokale Pfade (Ablage-Stamm etc.): config.toml (nicht committen).

Projektlayout (das Skript legt fehlende Dateien/Ordner beim ersten Start an):

    docsort/
    ├── docsort.py            <- dieses Skript
    ├── config.toml           <- lokale Konfiguration (NICHT committen)
    ├── config.example.toml   <- Vorlage (committen)
    ├── skills/
    │   └── classify.md       <- Skill: Anleitung, WIE klassifiziert wird
    ├── knowledge/
    │   └── categories.md     <- Knowledge: WAS die Kategorien bedeuten (v3)
    └── (Ablage-Ordner liegen ausserhalb, siehe config.toml)

Aufruf:
    python3 docsort.py                    # liest Automator-Output der Ablage
    python3 docsort.py --dry-run         # kopieren statt verschieben
    python3 docsort.py mein_test_ordner/  # anderer Eingangsordner
    python3 docsort.py --base-dir /pfad  # Ablage-Stamm ueberschreiben

Pipeline:
    Automator-Input  -> Mac-Automator (OCR-Scan) ->  Automator-Output
    Automator-Output -> docsort (Klassifizierung) -> Zielordner der Knowledge
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import shutil
import sys
import urllib.error
from pathlib import Path

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
SKILL_FILE = SCRIPT_DIR / "skills" / "classify.md"
KNOWLEDGE_FILE = SCRIPT_DIR / "knowledge" / "categories.md"
CONFIG_FILE = SCRIPT_DIR / "config.toml"

# Fallback, falls keine config.toml existiert
DEFAULT_BASE_DIR = Path.home() / "Documents/SynologyDrive/wolke7-Documents/private/Digitaler-Heim-Ordner"
# WICHTIG: docsort liest aus Automator-Output (dorthin liefert der Mac-Automator
# die OCR-gescannten PDFs). Automator-Input ist NUR Eingang des OCR-Workflows.
DEFAULT_INPUT_SUBDIR = "Automator-Output"
DEFAULT_OCR_INPUT_SUBDIR = "Automator-Input"
DEFAULT_LOG_SUBDIR = "Automator-log"

CONFIDENCE_THRESHOLD = 0.7  # Rule P4: darunter manuelle Klaerung
SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md"}
MAX_CHARS = 6000  # Kontext-Management: Dokumenttext wird hierauf gekuerzt

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "id":        {"type": "string"},
        "target_path": {"type": "string"},
        "year":      {"type": "string"},
        "confidence": {"type": "number"},
        "summary":   {"type": "string"},
    },
    "required": ["id", "target_path", "year", "confidence", "summary"],
}


def build_response_schema() -> dict:
    """Erzwingt Struktur UND gueltige Werte (Ollama Structured Outputs)."""
    ids = load_categories() + ["unsicher"]
    return {
        "type": "object",
        "properties": {
            "id":          {"type": "string", "enum": ids},
            "target_path": {"type": "string"},
            "year":        {"type": "string", "pattern": r"^\d{4}$"},
            "confidence":  {"type": "number"},
            "summary":     {"type": "string"},
        },
        "required": ["id", "target_path", "year", "confidence", "summary"],
    }

def load_config(override_base: str | None) -> dict:
    """Liest config.toml (falls vorhanden). Override per CLI gewinnt."""
    cfg = {
        "base_dir": str(DEFAULT_BASE_DIR),
        "input_subdir": DEFAULT_INPUT_SUBDIR,        # = Automator-Output
        "ocr_input_subdir": DEFAULT_OCR_INPUT_SUBDIR,  # = Automator-Input
        "log_subdir": DEFAULT_LOG_SUBDIR,
    }
    if CONFIG_FILE.exists():
        try:
            import tomllib  # Python >= 3.11
            data = tomllib.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except ImportError:
            data = {}
            # rudimentaerer Fallback-Parser: nur zeilenweise key = "value"
            for line in CONFIG_FILE.read_text(encoding="utf-8").splitlines():
                m = re.match(r'\s*(\w+)\s*=\s*"([^"]+)"', line)
                if m:
                    data[m.group(1)] = m.group(2)
        for key in cfg:
            if key in data:
                cfg[key] = str(data[key])
    if override_base:
        cfg["base_dir"] = override_base
    return cfg


# ---------------------------------------------------------------------------
# 1) Tool-Registry
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
            import pymupdf
            with pymupdf.open(path) as doc:
                text = "\n".join(page.get_text() for page in doc)
        except ImportError:
            return "[FEHLER] pymupdf ist nicht installiert: pip install pymupdf"
        if not text.strip():
            return "[WARNUNG] PDF enthaelt keinen Text – vermutlich ein Scan. OCR noetig (ocrmypdf)."
        return text
    return path.read_text(encoding="utf-8", errors="replace")

@tool("ask_model", "Stellt die Routing-Frage an das lokale Ollama-Modell.")
def ask_model(prompt: str, model: str) -> dict:
    import urllib.request

    payload = json.dumps({
        "model": model,
        "stream": False,
        "format": build_response_schema(),   # <- Schema erzwingt die 5 Felder  
        "options": {"temperature": 0},
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "http://localhost:11434/api/chat", data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read())
    except urllib.error.URLError as e:
        raise ConnectionError(f"Ollama nicht erreichbar ({e}). Laeuft 'ollama serve'?")
    except TimeoutError:
        raise ConnectionError(
            "Ollama hat innerhalb von 300s nicht geantwortet – "
            "Modell vorwaermen ('ollama run <modell>') oder kleineres Modell "
            "waehlen (--model llama3.2:3b).")
    return json.loads(data["message"]["content"])

@tool("move_file", "Verschiebt (dry-run: kopiert) eine Datei an den Zielpfad.")
def move_file(src: Path, dest_dir: Path, dry_run: bool) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)  # mehrstufige Pfade erlaubt
    dest = dest_dir / src.name
    if dest.exists():
        raise FileExistsError(f"Ziel existiert bereits: {dest}")
    if dry_run:
        shutil.copy2(src, dest)
    else:
        shutil.move(str(src), str(dest))
    return dest


# ---------------------------------------------------------------------------
# 2) Skills & Knowledge
# ---------------------------------------------------------------------------

SKILL_TEMPLATE = """# Skill: Dokument klassifizieren und routen

Du ordnest ein Dokument GENAU EINER Kategorie der Routing-Wissensbasis
(Kategorien-Definitionen und Matching-Hierarchie) zu und gibst den
Zielordner an.

Regeln:
1. Folge der Matching-Hierarchie (Abschnitt 3 der Knowledge): die erste
   hinreichend konfidente Kategorie gewinnt. Prioritaeten (HOCH) beachten.
2. Beurteile auf Basis des Dokumentinhalts, nicht des Dateinamens.
3. Uebernimme target_path NUR aus der Knowledge (mit Subtyp/Ordner-Regeln
   aus Abschnitt 2). Erfinde keine Pfade.
4. Bei CAT-07 (receipts-year) und CAT-09 (weg): year = Belegjahr aus dem
   Dokument (JJJJ). <JJJJ> im target_path bedeutet: dieses Jahr einsetzen.
5. Antworte NUR als JSON:
   {"id": "<Kategorie-ID>", "target_path": "<relativer Pfad>",
    "year": "<JJJJ oder null>", "confidence": 0.0-1.0,
    "summary": "ein Satz"}
6. confidence spiegelt deine Sicherheit wider. Bei Unsicherheit ehrlich
   niedrig antworten – niemals erfinden.
7. Trifft keine Kategorie zu: id = "unsicher", target_path = null.
"""

KNOWLEDGE_MINI_TEMPLATE = """# Knowledge: Kategorien (Platzhalter)

Dies ist ein Platzhalter. Die echte Routing-Wissensbasis (v3) gehoert hierher:
knowledge/categories.md aus dem docsort-Repo.
"""


def load_context() -> str:
    """Laedt Skill + Knowledge und baut den Systemkontext."""
    skill = SKILL_FILE.read_text(encoding="utf-8")
    knowledge = KNOWLEDGE_FILE.read_text(encoding="utf-8")
    return f"{skill}\n\n{knowledge}"


def load_categories() -> list[str]:
    """Parst alle Kategorie-IDs (- id: ...) aus der Knowledge-Datei.
    Waechst die Taxonomie, waechst das Harness ohne Codeaenderung mit."""
    text = KNOWLEDGE_FILE.read_text(encoding="utf-8")
    return re.findall(r"^- id:\s*(\S+)", text, re.MULTILINE)


def bootstrap(cfg: dict) -> None:
    """Legt Skill-, Knowledge- und Ablage-Systemordner beim ersten Start an."""
    for path, template in [(SKILL_FILE, SKILL_TEMPLATE),
                           (KNOWLEDGE_FILE, KNOWLEDGE_MINI_TEMPLATE)]:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(template, encoding="utf-8")
            print(f"[bootstrap] Vorlage angelegt: {path}")

    base = Path(cfg["base_dir"])
    if not base.is_dir():
        print(f"Fehler: Ablage-Stamm existiert nicht: {base}", file=sys.stderr)
        print("Hinweis: config.toml pruefen oder --base-dir angeben.", file=sys.stderr)
        sys.exit(1)
    # Bootstrap aller drei System-Ordner (falls der Mac-Automator sie noch
    # nicht angelegt hat): OCR-Eingang, OCR-Ausgang (= docsort-Eingang), Log
    for sub in (cfg["ocr_input_subdir"], cfg["input_subdir"], cfg["log_subdir"]):
        d = base / sub
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            print(f"[bootstrap] System-Ordner angelegt: {d}")


# ---------------------------------------------------------------------------
# 3) Execution Loop: Observe -> Think -> Act -> Verify
# ---------------------------------------------------------------------------

def parse_confidence(result: dict) -> float:
    """Guardrail: confidence kann String oder Prozentwert sein."""
    try:
        c = float(result.get("confidence", 0))
    except (TypeError, ValueError):
        return 0.0
    if c > 1.0:
        c /= 100.0     # Modell antwortet in Prozent (90 -> 0.9)
    return max(0.0, min(c, 1.0))


def build_target_path(result: dict) -> str | None:
    """Setzt <JJJJ> im target_path ein und validiert den Pfad (Rule N3)."""
    target = result.get("target_path")
    if not target or not isinstance(target, str):
        return None
    year = result.get("year")
    if "<JJJJ>" in target:
        if not (isinstance(year, str) and re.fullmatch(r"\d{4}", year)):
            return None  # Jahr noetig, aber nicht erkannt -> unsicher
        target = target.replace("<JJJJ>", year)
    # Guardrails: nur relative Pfade, kein Sprung nach oben, keine Systemordner
    p = target.strip().strip("/")
    if not p or ".." in p.split("/") or p.startswith("~"):
        return None
    if p.split("/")[0].startswith("Automator-") or p.split("/")[0] == "old-delete":
        return None
    return p


def classify_document(path: Path, context: str, model: str) -> dict:
    text = TOOLS["read_document"]["fn"](path)[:MAX_CHARS]
    if text.startswith(("[FEHLER", "[WARNUNG")):
        return {"id": "fehler", "target_path": None, "year": None,
                "confidence": 0.0, "summary": text}
    prompt = f"{context}\n\n--- DOKUMENT: {path.name} ---\n{text}"
    try:
        return TOOLS["ask_model"]["fn"](prompt, model)
    except ValueError:
        return {"id": "unsicher", "target_path": None, "year": None,
                "confidence": 0.0, "summary": "Modell-Antwort war kein gueltiges JSON"}


def verify(result: dict, valid_ids: list[str]) -> str | None:
    """Guardrail: Prueft die Modell-Antwort gegen die Regeln."""
    if result.get("id") not in valid_ids:
        return "unsicher"
    return None


def human_in_the_loop(result: dict, path: Path, categories: list[str]) -> dict:
    """Niedrige Konfidenz -> der Mensch entscheidet."""
    print(f"\n  Unsicher bei '{path.name}': "
          f"{result.get('id')} (Konfidenz {result.get('confidence')})")
    print("  Zusammenfassung:", result.get("summary", ""))
    for i, cat in enumerate(categories, 1):
        print(f"    {i}) {cat}")
    choice = input("  Ihre Wahl (Enter = unsicher, Datei bleibt liegen): ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(categories):
        return {"id": categories[int(choice) - 1], "target_path": None,
                "year": None, "confidence": 1.0,
                "summary": "manuell bestaetigt", "manual": True}
    return {"id": "unsicher", "target_path": None, "year": None,
            "confidence": 0.0, "summary": "vom Menschen uebersprungen",
            "manual": True}

def load_target_stems() -> list[str]:
    """Parst alle zulaessigen Zielordner-Staemme aus der Knowledge.
    System-Ordner (CAT-01) sind NIE Routing-Ziele (Rule N3)."""
    text = KNOWLEDGE_FILE.read_text(encoding="utf-8")
    stems = re.findall(r"^- target_path:\s*`([^`<]+)", text, re.MULTILINE)
    return [s.strip().rstrip("/") for s in stems
            if not s.strip().startswith("Automator-")]


def process_all(input_dir: Path, cfg: dict, model: str, dry_run: bool) -> None:
    bootstrap(cfg)
    context = load_context()
    categories = load_categories() + ["unsicher"]
    target_stems = load_target_stems()

    base = Path(cfg["base_dir"])
    log_dir = base / cfg["log_subdir"]
    log_path = log_dir / f"run_{datetime.datetime.now():%Y%m%d_%H%M%S}.jsonl"

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

        if verify(result, categories):
            result["raw_response"] = json.dumps(result, ensure_ascii=False)
            result["id"] = "unsicher"
        # Guardrail: erfundene Pfade verwerfen (nach ID-Check)
        tp = (result.get("target_path") or "").strip()
        if result["id"] != "unsicher" and not any(
                tp == s or tp.startswith(s + "/") for s in target_stems):
            result["raw_response"] = result.get("raw_response") or json.dumps(result, ensure_ascii=False)
            result["id"] = "unsicher"
            result["target_path"] = None
        result["confidence"] = parse_confidence(result)

        target_rel = build_target_path(result)

        if (result["confidence"] < CONFIDENCE_THRESHOLD or target_rel is None) \
                and result["id"] != "unsicher" and not result.get("manual"):
            result = human_in_the_loop(result, path, categories)
            target_rel = build_target_path(result) if result.get("target_path") else None
            if result["id"] != "unsicher" and target_rel is None:
                # manuelle Wahl ohne Pfad: Kategorie-Ordner als Fallback
                target_rel = result["id"]

        if result["id"] == "unsicher" or target_rel is None:
            print("  → unsortiert liegen gelassen (Rule P4)")
            dest = None
        else:
            try:
                dest = TOOLS["move_file"]["fn"](path, base / target_rel, dry_run)
                print(f"  → {result['id']}: {dest}")
            except (FileExistsError, shutil.Error) as e:
                print(f"  → [FEHLER] nicht verschoben: {e}")
                result["summary"] = f"Verschieben fehlgeschlagen: {e}"
                dest = None

        stats[result["id"]] = stats.get(result["id"], 0) + 1
        with log_path.open("a", encoding="utf-8") as log:  # Rule P3
            log.write(json.dumps({
                "file": path.name,
                "id": result["id"],
                "target": str(dest) if dest else None,
                "confidence": result["confidence"],
                "summary": result.get("summary", ""),
                "raw_response": result.get("raw_response"),   # <- ergaenzen
                "dry_run": dry_run, "model": model,
            }) + "\n")

    print("\nZusammenfassung:", ", ".join(f"{k}={v}" for k, v in stats.items()))
    print(f"Protokoll: {log_path}")


# ---------------------------------------------------------------------------
# 4) CLI-Einstieg
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Mini-Harness: Dokumente sortieren")
    parser.add_argument("input", type=Path, nargs="?",
                        help="Eingangsordner (Standard: Automator-Output der Ablage)")
    parser.add_argument("--base-dir", default=None,
                        help="Ablage-Stamm ueberschreiben (sonst config.toml)")
    parser.add_argument("--model", default="llama3.1:8b", help="Ollama-Modell")
    parser.add_argument("--dry-run", action="store_true",
                        help="Kopieren statt Verschieben (Guardrail fuer Tests)")
    args = parser.parse_args()

    cfg = load_config(args.base_dir)
    input_dir = args.input if args.input else Path(cfg["base_dir"]) / cfg["input_subdir"]

    if not input_dir.is_dir():
        print(f"Fehler: {input_dir} ist kein Verzeichnis.", file=sys.stderr)
        return 1
    try:
        process_all(input_dir, cfg, args.model, args.dry_run)
    except ConnectionError as e:
        print(f"Fehler: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
