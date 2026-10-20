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
5. Antworte NUR als JSON mit GENAU diesen Feldern (keine anderen
   Schluessel, keine deutschen Feldnamen!):
   {"id": "receipts-year", "target_path": "Quittungen etc nach Jahr/2026",
    "year": "2026", "confidence": 0.9, "summary": "Renteninformation 2026"}
   Das ist ein BEISPIEL fuer das Format. Pruefe jedes Dokument neu und
   waehle die passende id und den passenden target_path aus der Knowledge.
   Deine Antwort muss mit "{'id'" beginnen.
6. confidence spiegelt deine Sicherheit wider. Bei Unsicherheit ehrlich
   niedrig antworten – niemals erfinden.
7. Trifft keine Kategorie zu: id = "unsicher", target_path = null.