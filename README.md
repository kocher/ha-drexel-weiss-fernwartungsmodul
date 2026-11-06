# Drexel und Weiss Aerosmart (Home-Assistant-Custom-Integration)

Liest den Werte-Endpunkt des **Drexel und Weiss Aerosmart Fernwartungsmoduls**,
das die Wärmepumpen-Daten bereitstellt. Ersetzt den `rest:`-Block durch eine
pollende Integration: eine Anfrage pro Zyklus versorgt alle Sensoren und
Binärsensoren.

## Installation

1. `custom_components/drexel` nach `<config>/custom_components/drexel` kopieren.
2. Home Assistant neu starten.
3. Einstellungen → Geräte & Dienste → Integration hinzufügen →
   **Drexel und Weiss Aerosmart**.
4. Host, Port, Pfad (Standard: `334`, `/dw`) und Abfrageintervall des
   Fernwartungsmoduls eingeben.
5. Den alten `rest:`-Block aus `rest.yml` / `configuration.yaml` entfernen und
   die alten REST-Entitäten in der Entitäts-Registry löschen, sonst bekommen die
   neuen Entitäten ein `_2`-Suffix.

Das Abfrageintervall beträgt standardmäßig 60 s und kann über **Konfigurieren**
der Integration geändert werden (10–3600 s). Um einen weiteren Parameter
hinzuzufügen, der nicht automatisch angelegt wird, in `api.py` unter
`EXTRA_PARAMETERS` seine `parameterId` mit Einheit und Skalierung ergänzen und
neu starten.

## Entitäten

Beim Start liest die Integration Texte (`?area=languages`, in der Sprache von
Home Assistant), Geräte (`?area=hardware`) und Parameter-Metadaten
(`?area=options`, `betriebsart`, `tempconfig`) und legt daraus die Entitäten so
an, wie sie das Web-Interface des Moduls zeigt:

- **Aerosmart Wärmepumpe / Lüftung / Raumbediengerät**: eigene Geräte mit
  Seriennummer und Softwareversion, je Gerät
  - alle Werte des Statusbereichs als Sensor bzw. Binärsensor (Temperaturen,
    Drehzahlen, Relaiskontakte, Anforderungen, Betriebsstunden, …), dazu
    **Boiler** (`T_BOILER`) an der Wärmepumpe,
  - alle im Bereich „Betrieb“ änderbaren Einstellungen als Number, Select
    oder Switch (Kategorie *Konfiguration*), z. B. Smart-Grid-Modus,
    Heiz-/Kühlgrenze, Party-Dauer, CO₂-Zielwerte. Einstellungen, bei denen das
    Gerät neu startet, sind standardmäßig deaktiviert. Werks-Reset und
    „History löschen“ werden nie angeboten,
  - **Betriebsart** (Select), **Raum-Soll** und **Brauchwasser** (Number) – die
    Bedienung des Dashboards – an dem Gerät, das den Wert meldet; die Sollwerte
    zusätzlich als Sensor für die Langzeitstatistik.
- **Raum** (Climate, am Raumbediengerät): Raumtemperatur, Raum-Soll und die
  Betriebsart als Preset, Heizen/Kühlen/Leerlauf aus dem WP-Betriebsstatus.
  Einziger HVAC-Modus ist „Heizen“, da das Gerät keinen Heizungs-Ausschalter
  hat.
- **Brauchwasser** (Water Heater, an der Wärmepumpe): Boilertemperatur und
  Brauchwasser-Soll; Zustand immer „Wärmepumpe“.
- **Fernwartungsmodul**: **Störung** (`?area=errors`) und **Informationen**
  (`?area=informations`), Device Class `problem`, die Meldungstexte stehen im
  Attribut `meldungen`.

Zahlenwerte, die das Modul nicht meldet, werden wie im Web-Interface als 0
angezeigt.

### Umstieg von Version 0.0.7 und älter

Die früheren, fest programmierten Entitäten („Aerosmart Boiler“, „Aerosmart
Raum“, …) gibt es nicht mehr. Beim ersten Start übernimmt jeweils die
entsprechende Entität des Geräts ihren Registry-Eintrag: die `entity_id` bleibt
gleich, damit auch Verlauf, Langzeitstatistik, Automationen und Dashboards.
Nur Name und Gerät ändern sich (z. B. `sensor.aerosmart_boiler` heißt jetzt
„Aerosmart Wärmepumpe Boiler“).

Schreiben erfolgt wie im Web-Interface per `POST <pfad>` mit
`[{"parameterId", "deviceId", "value"}]`; danach wartet die Integration bis zu
10 s, bis `?area=lastchanges` die Änderung bestätigt. Details zur API:
[docs/API.md](docs/API.md).

Pro Abfragezyklus werden `?area=values`, `?area=errors` und
`?area=informations` gelesen.

## Lizenz

[MIT](LICENSE) – freie Nutzung, Änderung und Weitergabe, Namensnennung und
Lizenztext müssen erhalten bleiben, keine Gewährleistung.
