# Skill: Dokument klassifizieren und routen

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