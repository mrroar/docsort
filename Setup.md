# Setup – docsort in 10 Minuten einrichten

Diese Anleitung führt vom leeren Mac zum ersten Testlauf. Die Befehle sind für ein Terminal (zsh) gedacht.

## Voraussetzungen prüfen

```bash
# Git vorhanden?
git --version

# Python 3 vorhanden?
python3 --version
```

Falls Git fehlt: macOS fragt bei der ersten Nutzung automatisch nach den Command Line Tools – bestätigen. Alternativ vorab installieren:

```bash
xcode-select --install
```

## Schritt 1: Projektordner anlegen

```bash
mkdir docsort && cd docsort
```

## Schritt 2: docsort.py speichern

Die Datei `docsort.py` aus dem Code-Artefakt in diesem Ordner speichern. Beim ersten Start legt das Skript fehlende Verzeichnisse und Vorlagen (`skills/classify.md`, `knowledge/categories.md`, `logs/`) automatisch selbst an.

## Schritt 3: Ollama installieren

**Variante A – Direkter Installer (empfohlen, besonders auf Intel-Macs):**

Ollama von **ollama.com/download** als macOS-Paket (dmg) laden, in den Programme-Ordner ziehen und starten. Die App läuft als Menüleisten-Dienst, das CLI `ollama` wird automatisch im Pfad bereitgestellt.

> **Hintergrund:** Homebrew liefert für Intel-Macs kaum noch fertige Pakete (Tier 3). Der direkte Installer umgeht das Problem vollständig.

**Variante B – Homebrew (Apple Silicon):**

```bash
brew install ollama && ollama serve   # zweites Terminal, falls die App nicht läuft
```

**Prüfen, ob Ollama läuft:**

```bash
ollama --version
```

## Schritt 4: Modell laden

```bash
ollama pull llama3.1:8b
```

Alternativ (schneller auf Intel-CPU, etwas weniger präzise):

```bash
ollama pull llama3.2:3b
```

> Beide laden und danach per `--model` umschaltbar – gut für einen späteren Vergleich.

## Schritt 5: Virtuelle Umgebung + Python-Abhängigkeit

```bash
# Virtuelle Umgebung anlegen (einmalig, liegt im Projektordner)
python3 -m venv .venv

# Umgebung aktivieren – in JEDEM neuen Terminal vor der Nutzung
source .venv/bin/activate

# pymupdf NUR in der Umgebung installieren
pip install pymupdf
```

> **Warum venv?** Ohne Umgebung landet `pip3 install` global im System-Python – Pakete verschiedener Projekte kollidieren, und macOS-Updates können Installationen zerschießen. Die venv kapselt alles Projektlokale im Ordner `.venv/`.
>
> **Alltagstipps:** Nach dem Aktivieren steht im Prompt `(.venv)`. Verlassen per `deactivate`. Neues Terminal = erneut `source .venv/bin/activate` vor jedem Lauf.
>
> Hinweis: In der aktivierten Umgebung heißt der Befehl `pip` (nicht `pip3`) und `python` (nicht `python3`) – beide zeigen auf die Umgebung.

(Für Text-Extraktion aus PDFs. Für eingescannte PDFs zusätzlich optional: `brew install ocrmypdf` – das ist ein eigenständiges Programm und gehört nicht in die venv.)

## Schritt 6: Ordner für Testdaten anlegen

```bash
mkdir input
# 2–3 Testdateien hineinlegen: z. B. eine Rechnung, einen kurzen „Vertrag“,
# eine unklare Textdatei (jeweils .pdf, .txt oder .md)
```

## Schritt 7: Erster Testlauf

```bash
# falls noch nicht aktiv:
source .venv/bin/activate

python3 docsort.py input/ --dry-run
```

Der Dry-Run **kopiert** Dateien nur in den Zielordner (`archiv/`, Standard) und fragt bei niedriger Konfidenz interaktiv nach Ihrer Entscheidung – es geht nichts verloren.

Erwartete Ausgabe (Beispiel):

```
3 Datei(en) – Modus: DRY-RUN (kopieren) – Modell: llama3.1:8b

→ rechnung_mai.txt
  → rechnung: archiv/rechnung/rechnung_mai.txt
→ vertrag_strom.md
  → vertrag: archiv/vertrag/vertrag_strom.md
...
Zusammenfassung: rechnung=1, vertrag=1, ...
Protokoll: logs/run_20261018_....jsonl
```

## Schritt 8: Ergebnisse prüfen

```bash
# Wo landeten die Dateien?
ls -R archiv

# Protokoll ansehen (eine Zeile pro Dokument, JSON)
cat logs/run_*.jsonl
```

## Schritt 9: Echtlauf (Verschieben)

Erst wenn der Dry-Run zufriedenstellend klassifiziert:

```bash
python3 docsort.py input/ --target archiv/
```

Ohne `--dry-run` werden Dateien **verschoben** – sie liegen danach nicht mehr in `input/`.

## Häufige Fehler und Lösungen

| Problem | Ursache | Lösung |
|---|---|---|
| `URLError` / Verbindung verweigert | Ollama läuft nicht | Ollama-App starten oder `ollama serve` |
| `[FEHLER] pymupdf ist nicht installiert` | Schritt 5 ausgelassen | `pip3 install pymupdf` |
| `[WARNUNG] PDF enthaelt keinen Text` | Eingescannte PDF (Bild) | OCR: `ocrmypdf eingabe.pdf ausgabe.pdf` |
| Modell-Antwort kein gültiges JSON | Modell zu schwach / Prompt | Anderes Modell testen (`--model llama3.1:8b`) |
| `Fehler: ... ist kein Verzeichnis` | Pfad falsch | Eingangsordner prüfen bzw. `mkdir input` |

## Git (optional): Setup ins Repo übernehmen

```bash
cd docsort
git init            # falls noch kein Repo geklont
git add docsort.py skills knowledge
git commit -m "feat: Harness-Grundgerüst mit Skill und Knowledge"
```

Laufzeitdaten (`logs/`, `archiv/`, `input/`) nicht committen – in `.gitignore` eintragen:

```
logs/
archiv/
input/
.venv/
__pycache__/
```