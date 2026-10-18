# docsort – Mini-Harness zur Dokumentenklassifizierung

Ein Lernprojekt: ein selbst gebauter **AI Harness**, der Dokumente aus einem Ordner analysiert und per lokal laufendem LLM (Ollama) in Kategorien-Ordner sortiert. Manuell ausgelöst – kein Hintergrunddienst, keine Cloud.

## Was ist ein Harness? (Das Konzept hinter diesem Projekt)

Ein **AI Agent** ist das „Gehirn“: das Modell, das entscheidet (probabilistisch, kreativ).
Ein **AI Harness** ist die Umgebung, die dieses Gehirn erst handlungsfähig und sicher macht (deterministisch, regelbasiert):

- **Tool Registry**: Werkzeuge mit klarer Schnittstelle (hier: `read_document`, `ask_model`, `move_file`)
- **Skills**: Anleitungen, *wie* eine Aufgabe auszuführen ist (Markdown-Dateien, editierbar ohne Code)
- **Knowledge**: Domänenwissen, *was* Begriffe bedeuten (Kategorienliste, getrennt vom Code)
- **Guardrails**: erzwungenes JSON, Kategorien-Validierung, `--dry-run`, Human-in-the-Loop
- **State & Logging**: JSONL-Protokoll pro Durchlauf als Grundlage für Verbesserung

## Projektstruktur

```
docsort/
├── docsort.py            # das Harness-Skelett (~250 Zeilen)
├── skills/
│   └── classify.md       # Skill: Anleitung zum Klassifizieren
├── knowledge/
│   └── categories.md     # Knowledge: Kategorien & Definitionen
├── logs/                 # JSONL-Protokolle je Lauf (nicht committen)
├── input/                # zu sortierende Dateien
└── archiv/               # Zielordner (entsteht pro Kategorie)
```

`docsort.py` legt Skill- und Knowledge-Vorlagen beim ersten Start selbst an.

## Voraussetzungen (macOS)

| Werkzeug | Zweck | Hinweis |
|---|---|---|
| Ollama | lokale LLM-Laufzeit | Direkt von ollama.com/download (dmg); auf Intel-Macs empfohlen statt Homebrew |
| llama3.1:8b oder llama3.2:3b | Klassifikationsmodell | 8b = genauer, 3b = schneller auf Intel-CPU |
| pymupdf | PDF-Textextraktion | `pip3 install pymupdf` |
| Git + SSH-Key | Versionskontrolle | `ssh-keygen -t ed25519`, Public Key auf GitHub hinterlegen |

> **Hinweis Intel-Mac:** Homebrew dort ist nur noch Tier 3 (keine fertigen Pakete). Ollama direkt per Installer beziehen; die Xcode Command Line Tools (`xcode-select --install`) sind Voraussetzung für alles, was kompiliert.

## Verwendung

```bash
# 1. Ollama starten (App oder CLI) und Modell laden
ollama pull llama3.1:8b

# 2. Testlauf: kopiert nur, fragt bei niedriger Konfidenz nach
python3 docsort.py input/ --dry-run

# 3. Echtlauf: verschiebt
python3 docsort.py input/ --target archiv/

# Alternatives Modell
python3 docsort.py input/ --dry-run --model llama3.2:3b
```

Ablauf pro Dokument: **Observe** (Text extrahieren, auf 6.000 Zeichen kürzen) → **Think** (ein LLM-Aufruf, JSON-Antwort erzwingen) → **Act** (verschieben/kopieren) → **Verify** (Kategorie validieren, Konfidenz prüfen).

## Lernpfad: das hilft wirklich beim Verständnis

1. **Dry-Run mit 3 Testdateien** (Rechnung, Vertrag, etwas Unklares) – Protokoll in `logs/` ansehen.
2. **Skill verfeinern**: `skills/classify.md` um Beispiele erweitern und erneut laufen lassen – Unterschiede im Protokoll vergleichen. Genau hier spürt man, was „Prompt/Skill-Engineering“ bedeutet.
3. **Knowledge erweitern**: Kategorie in `knowledge/categories.md` ergänzen – das System kennt sie danach automatisch (Validierung gegen dieselbe Liste).
4. **Modellvergleich**: `llama3.2:3b` vs. `llama3.1:8b` am selben Eingangsordner; Konfidenz und Fehler im JSONL-Protokoll vergleichen.
5. **Bekannte Optimierungen** (gute Übungsaufgaben):
   - Konfidenz robust parsen (`float(...)` mit try/except – Modell antwortet teils als String)
   - `URLError` abfangen mit klarem Hinweis, wenn Ollama nicht läuft
   - Kategorienliste zur Laufzeit aus der Knowledge-Datei parsen statt im Code duplizieren
6. **Erweiterung Richtung echter Agent**: mehrstufige Verarbeitung (z. B. mehrseitige Dokumente mit gemischtem Inhalt) – daraus wird eine echte Observe-Think-Act-Schleife mit mehreren Tool-Aufrufen pro Dokument.

## Git & SSH auf dem Mac (Einrichtungsnotizen)

```bash
ssh-keygen -t ed25519 -C "email@example.com"
cat ~/.ssh/id_ed25519.pub | pbcopy     # auf GitHub unter Settings → SSH and GPG keys einfügen
ssh -T git@github.com                  # Test: "Hi mrroar! ..."
git clone git@github.com:mrroar/docsort.git
```

Diagnose bei `Permission denied (publickey)`: `ssh -vT git@github.com` zeigt, welcher Key angeboten wird (`Offering public key: ...`). Git selbst braucht keinen Key – SSH authentifiziert, Git nutzt SSH nur als Transport. Der SSH-Agent merkt sich die Passphrase via macOS-Keychain (`ssh-add --apple-use-keychain ~/.ssh/id_ed25519`).

## Lessons Learned: Integrationen und Berechtigungen

Der Versuch, einen Chat-Agenten per Connector an ein privates GitHub-Repo anzubinden, endete in einer kleinen Lehreinheit über Berechtigungsmodelle:

- **„Verbunden“ heißt nicht „voller Zugriff“**: Ein Connector-Token hat exakt die Scopes, die bei der Autorisierung erteilt wurden – hier: nur öffentliche Repos. Private Repos blieben unsichtbar (API meldet 404 statt 403; GitHub verrät nicht mal die Existenz).
- **OAuth-App vs. GitHub-App**: OAuth-Apps autorisieren das ganze Konto mit festen Scopes; GitHub-Apps werden pro Repository installiert und zugewiesen.
- **Leerer Anfangszustand**: Ein frisch angelegtes Repo ohne Commit liefert 404 – noch nicht mal `main` existiert dann.
- **Pragmatismus**: Kurzes, kontrolliertes Umstellen auf public (nur Lernprojekt ohne sensible Daten) hat die Diagnose in eine Bestätigung verwandelt.
- **Zusammenarbeit ohne Connector-Rechte** funktioniert trotzdem: Diffs und Protokolle in den Chat, Reviews und Code als Artefakt zurück – der Agent ist das Transportband, nicht die Blockade.

## Abgrenzung: Warum kein OpenCode?

OpenCode als Coding-Agent-Harness wäre hier möglich gewesen, aber für die Klassifikations-Pipeline ein Overkill: Sie brauchen keine Codegenerierung, sondern eine deterministische Pipeline mit einem LLM-Aufruf pro Dokument. Der Selbstbau-Harness macht jede Komponente sichtbar – wer Tools, Skills und Guardrails einmal selbst gebaut hat, liest Framework-Dokumentationen (LangGraph, OpenCode, Agenten-SDKs) danach mit ganz anderen Augen.

## Roadmap (optional)

- [ ] OCR für Scans (`ocrmypdf` bei textlosen PDFs)
- [ ] Automatische Dateiumbenennung nach Schema (z. B. `rechnung_2026-10-18_absender.pdf`)
- [ ] Konfidenz-Schwellwert konfigurierbar pro Kategorie
- [ ] Zweistufige Klassifikation bei Mehrthemen-Dokumenten (Agenten-Schleife)