---
type: taxonomy
domain: document-filing
project: Dokumenten Automation
owner: Daniel Hess
version: 3
updated: 2026-10-19
language: de
purpose: >
  Routing-Wissensbasis für ein Dokumenten-Automatisierungs-Harness.
  Ordnet jeden Dokumenttyp genau einem Zielordner der Dokumentenablage zu.
---

# Dokumenten-Kategorien (Routing-Wissensbasis)

Dieses File ist die maschinenlesbare Zuordnungsregel für die automatische
Dokumentenablage. Ein Dokument wird über die Matching-Regeln (Abschnitt 3)
einer Kategorie zugeordnet und in deren `target_path` abgelegt.

## 1. Pipeline-Konventionen

| Pfad | Rolle |
|---|---|
| `Automator-Input` | Watch-Folder: neue, unverarbeitete Dokumente |
| `Automator-Output` | Verarbeitete Dokumente, final einsortiert |
| `Automator-log` | Verarbeitungsprotokoll je Lauf |

Regeln:

- Rule P1: Eingehende Dokumente liegen ausschließlich in `Automator-Input`.
- Rule P2: Nach Kategorisierung wird das Dokument verschoben (nicht kopiert).
- Rule P3: Jede Entscheidung wird in `Automator-log` protokolliert
  (Dokumentname, erkannte Kategorie, Zielpfad, Konfidenz).
- Rule P4: Ist keine Kategorie mit Konfidenz ≥ 0.7 bestimmbar,
  verbleibt das Dokument in `Automator-Input` und wird zur manuellen
  Klärung markiert.

## 2. Kategorien-Definitionen

Jede Kategorie: `id` (stabil), `name`, `target_path`, `match` (Kriterien),
`exclude` (Ausschlüsse), Beispiele.

### CAT-01: Automator-Pipeline
- target_path: `Automator-Input` / `Automator-Output` / `Automator-log`
- Zweck: Nur System-Ordner; niemals Ziel einer Kategorisierung.

### CAT-02: Persönliche Dokumente
- id: personal
- target_path: `Persoenliche-Dokumente-sehr-wichtig/<Unterordner>`
- match: amtliche Urkunden und Ausweise (Original-Dokumente), Zuordnung per Subtyp:
  - Diplom → `Diplom`
  - Schul-/Ausbildungszeugnisse → `Zeugnisse`
  - Sozialversicherungsausweis → `Sozialversicherungsausweis`
  - Personalausweis/Reisepass → `Personalausweis`
  - Kredit-/EC-/VISA-Karten, Kartenabrechnungen → `VISA EC Karten`
  - Heiratsurkunde → `Heiratsurkunde`
- priority: HOCH (amtliche Dokumente gewinnen gegen alle anderen Kategorien)

### CAT-03: Banken & Versicherungspolicen
- id: bank-policies
- target_path: `Banken und Versicherungsunterlagen_Policen - Keine Auszuege`
- match: Versicherungspolicen, Versicherungsbedingungen, Bank-Vertragsunterlagen
- exclude: Kontoauszüge (→ CAT-11 Zeit-WEG-Regel bzw. CAT-07), Police eines
  Ordners aus CAT-04 (spezifischerer Ordner gewinnt)

### CAT-04: Versicherungen & Arbeitsverträge
- id: contracts
- target_path: `Versicherungen-Arbeitsvertraege/<Anbieter-Ordner>`
- match: Ordnerschlüssel in Absender/Inhalt (Fallback: neues Jahr/Brief;
  dann keine Zuordnung möglich → P4).
- Anbieter-Ordner:
  - `Gothaer-Lebensv-Daniel-Binect-ruht` – Gothaer Lebensversicherung Daniel (beitragsfrei, Binect)
  - `Nuernberger-Lebensv-Tabitha` – Nürnberger Lebensversicherung Tabitha
  - `Signal Iduna` – Signal Iduna Verträge
  - `AOK-Daniel` – AOK-Krankenkasse Daniel
  - `BKK-Tabitha` – BKK-Krankenkasse Tabitha
  - `TK-Tabitha` – Techniker Krankenkasse Tabitha
  - `WGV-Auto` – Kfz-Versicherung WGV
  - `WGV-Haftpflicht-Hausrat` – Haftpflicht/Hausrat WGV
  - `em-Arbeitsvertrag` – Arbeitsvertrag em (Kanzlei/AG, Unklarheit akzeptiert)
  - `Cfan-Arbeitsvertrag` – Arbeitsvertrag Cfan
  - `em-MAG` – MAG-Vertrag em
  - `em-Metall-Rente-Daniel` – betriebliche Metall-Rente Daniel
  - `Erbe-Daniel` – Erbschafts-/Nachlassunterlagen Daniel
- exclude: AOK/BKK/TK-Leistungsabrechnungen oder Attest-Arzt-Dokumente
  (→ CAT-08, wenn ärztlicher Inhalt dominiert)

### CAT-05: Mile
- id: mile
- target_path: `Mile/<Unterordner>`
- match: Absender/Kontext = Mile ist ein Hund ; Subtypen:
  - Tier-Arzt, Tierarzt/ärztliche Behandlung, Medikamente -> `Arzt`
  - Hunde- Haftpflicht WGV → `WGV Haftpflicht`
  - Operationskostenversicherung → `R-u-V-Operationskostenversicherung`

### CAT-06: Auto
- id: auto
- target_path: `Auto/<Fahrzeug>`
- match: Dokumente zu Fahrzeugen TT oder Caddy (Werkstatt, Zulassung, TÜV, Rechnungen)
- routing: Kennung "TT" → `Auto/TT`, Kennung "Caddy" → `Auto/Caddy`

### CAT-07: Quittungen & Belege nach Jahr
- id: receipts-year
- target_path: `Quittungen etc nach Jahr/<JJJJ>`
- match: alltägliche Quittungen, Kaufbelege, Rechnungen des Konsums/Alltags
- routing: Jahr des Belegdatums → Ordner `2025` / `2026` / fortlaufend
- exclude: Kassenzettel/Rechnungen für WEG-Konten (→ CAT-09);
  Belege zu Anschaffungen mit Garantie (→ CAT-10)

### CAT-08: Arztsachen
- id: medical
- target_path: `Arztsachen/<Unterordner>`
- match: Arztbriefe, Atteste, Befunde, Patientenverfügungen
- routing:
  - Patientenverfügung Daniel → `Patientenverfuegung-Daniel`
  - Patientenverfügung Tabitha → `Patientenverfuegung-Tabitha`
  - ärztliche Unterlagen Daniel → `Daniel`
  - ärztliche Unterlagen Tabitha → `Tabitha`
- priority: HOCH bei Patientenverfügungen (dominantes Dokument)
- exclude: Tierarzt-/Tierbehandlung (Patient ist ein Hund also ein Tier) -> CAT-05 Mile/Arzt

### CAT-09: WEG (vereinfacht, v3)
- id: weg
- target_path: `WEG/<JJJJ>`
- match: WEG-Dokumente (Korrespondenz, Abrechnungen, Protokolle, Belege),
  NUR wenn sie explizit durch den Owner in `Automator-Input`/`Automator-Output`
  gelegt werden; Routing allein nach Dokumenten-/Belegjahr → Unterordner Jahr.
- Hinweis: Die allermeisten WEG-Dokumente kommen als ZIP und werden manuell
  einsortiert – sie durchlaufen den Automator nicht. Kein HKV-Konto-Routing
  und kein Subrouting mehr (v2-Regeln ersetzt); HKV-Kontenplan nur noch
  Referenz für manuelle Sortierung.
- exclude: `old-delete` ist obsolet; niemals neues Dokument dort ablegen;
  Aufruf an Owner: Inhalt kann gelöscht werden.

### CAT-10: Sach-Dokumentation (nur digital)
- id: asset-docs
- target_path: `Sach-Dokumentation-nurDigital/<Objekt>`
- match: Kaufverträge, Garantien, Handbücher, Montage-/Serviceunterlagen
  für dokumentierte Objekte
- Objekt-Zuordnung:
  - `Gabriel-Klaiber-Markise` – Markise (Firma Klaiber)
  - `Bosch DIY` – Bosch-Werkzeuge/-Geräte
  - `Segmueller-Alno-Kueche` – Küche Segmüller/Alno
  - `Tamya Alpine A110` – Tamiya Modellauto Alpine A110

### CAT-11: Roter-Ordner (Notfallordner)
- id: emergency-folder
- target_path: `Roter-Ordner`
- match: Übersichtsdokumente für den Ernstfall (Notfallkonten-Liste,
  Vollmachten, Versicherungszusammenfassungen, Bestattungsvorsorge)
- priority: NUR wenn das Dokument explizit als Notfall-/Übersichtsdokument
  erkennbar ist; sonst gewinnt die spezifischere Kategorie

## 3. Matching-Hierarchie (Entscheidungsreihenfolge)

Das Harness prüft in dieser Reihenfolge; die erste hinreichend
konfidente Kategorie gewinnt:

1. CAT-08 Patientenverfügung (explizit „Patientenverfügung")
2. CAT-02 amtliche Urkunden (Original-Dokumentcharakter)
3. CAT-09 WEG (Absender Verwalter/WEG; nur bei expliziter Übergabe, Jahr extrahieren)
4. CAT-05 Mile (Absender Mile)
5. CAT-04 konkreter Anbieter-Ordner (Absender = gelisteter Anbieter)
6. CAT-06 Fahrzeug TT/Caddy
7. CAT-10 dokumentierte Objekte
8. CAT-11 Roter-Ordner (Notfall-Charakter)
9. CAT-03 allgemeine Police/Bank-Unterlage
10. CAT-07 allgemeine Quittung (nach Jahr)

## 4. HKV-Kontenplan (nur Referenz für manuelle ZIP-Sortierung)

Belege der WEG-Belegprüfung werden nach HKV-Konto in den numerischen
Unterordner von `Belege 2025/` einsortiert. Zuordnung: Belegtext/Rechnungssteller → Konto.

| Konto | Bezeichnung | Typische Rechnungssteller/Stichworte |
|---|---|---|
| 91900 | Rechnungsabgrenzung | Abgrenzung, vorausbezahlte Leistungen |
| 94000 | Müllabfuhr | Entsorger, Abfall, Mülltonne |
| 94002 | Niederschlagswasser | Regenwasser, Entwässerung |
| 94100 | Strom | Energieversorger, Stromrechnung |
| 94120 | Wasser | Wasserwerk, Wassergebühr |
| 94130 | Kanal | Kanalgebühr, Abwasser |
| 94200 | Versicherungen | WEG-Verbandspolicen, Gebäuderversicherung |
| 94300 | Heizungskosten | Heizöl, Gas, Heizungswartung, Betriebskosten Heizung |
| 94310 | Kaminkehrer | Kaminkehrer, Schornsteinfeger |
| 94500 | Laufende Instandhaltungsarbeiten | Handwerkerrechnungen Instandhaltung |
| 94535 | Wartung Rauchwarnmelder | Rauchwarnmelder-Wartung |
| 94700 | Hausmeister | Hausmeistervergütung |
| 94701 | Treppen- u. Hausreinigung | Reinigungsfirma, Treppenhausreinigung |
| 94960 | Rechts- u. Beratungskosten | Anwalt, Verwalterberatung, Rechtsstreit |
| 94970 | Gartenpflege | Gärtner, Grünpflege |
| 95310 | Saalmiete | Raum-/Saalmiete (Versammlung) |
| 95400 | Hausbank | Bankgebühren WEG-Konto |
| 95500 | Sondereigentum | Instandhaltung Sondereigentum (Sonderumlage) |
| 98000 | Hausbank | Zinsen/Disagio WEG-Konto |

## 5. Personen- und Naming-Regeln

- Rule N1: Personen werden konsequent getrennt: Daniel und Tabitha erhalten
  getrennte Ordner; bei Namensnennung immer dementsprechend routen.
- Rule N2: Ordner im Zielbstamm vorhanden → nicht neu anlegen, sondern nutzen;
  fehlt ein Ordner (z. B. neues Belegjahr, neuer Anbieter), vor Anlage in
  `Automator-log` markieren und Kategorie-Owner bestätigen lassen.
- Rule N3: Keine Zuordnung in System-Ordner (`Automator-*`) oder
  `old-delete`-Ordner.
- Rule N4: Belege mit Datum → Zielordner-Jahr = Belegjahr (CAT-07 und CAT-09).
