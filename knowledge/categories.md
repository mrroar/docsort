---
type: taxonomy
domain: document-filing
project: Dokumenten Automation
owner: Daniel Hess
version: 5
updated: 2026-10-20
language: en
purpose: >
  Routing-Wissensbasis für ein Dokumenten-Automatisierungs-Harness.
  Ordnet jeden Dokumenttyp genau einem Zielordner der Dokumentenablage zu.
---

# Knowledge: Categories (v5, simplified)

Match by these keywords (German document content). The first matching
category in this list wins.

- id: receipts-year
  folder: Quittungen etc nach Jahr/<JJJJ>
  keywords: Quittung, Beleg, Rechnung, Kaufbeleg, Rentenbescheid,
  Renteninformation, Deutsche Rentenversicherung

- id: contracts
  folder: Vertraege-und-Kuendigungen/<Person-Unternehmen>
  keywords: Vertrag, Kündigung, Police, Versicherungsschein,
  Arbeitsvertrag, Tarifvertrag, Nachlass, Erbschaft

- id: mile
  folder: Mile
  keywords: Mile, Hund, Tierarzt, Hundesteuer

- id: auto
  folder: Auto
  keywords: Fahrzeug, Kfz, Werkstatt, TÜV, Zulassung, Audi TT, Caddy

- id: medical
  folder: Arztsachen
  keywords: Arzt, Krankenhaus, Attest, Leistungsabrechnung, Rezept

- id: personal
  folder: Persoenliche-Dokumente-sehr-wichtig
  keywords: Urkunde, Zeugnis, Geburtsurkunde, Reisepass, Führerschein

- id: weg
  folder: WEG
  keywords: WEG, Eigentümerversammlung, Hausverwalter, HKV

- id: unsicher
  folder: (leave in place, no routing)
  keywords: none – fallback only