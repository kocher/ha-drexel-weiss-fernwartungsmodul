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
hinzuzufügen, der nicht automatisch angelegt wird, in `const.py` einen
`SensorDef`/`BinarySensorDef` mit seiner `parameter_id` ergänzen und neu
starten.

## Entitäten

Beim Start liest die Integration Texte (`?area=languages`, in der Sprache von
Home Assistant), Geräte (`?area=hardware`) und Parameter-Metadaten
(`?area=options`, `betriebsart`, `tempconfig`) und legt daraus die Entitäten so
an, wie sie das Web-Interface des Moduls zeigt:

- **Fernwartungsmodul** (wie bisher): die bisherigen Sensoren und
  Binärsensoren, dazu
  - **Aerosmart Betriebsart** (Select), **Aerosmart Raum Soll** und
    **Aerosmart Brauchwasser Soll** (Number) – die Bedienung des Dashboards,
  - **Aerosmart Störung** (`?area=errors`) und **Aerosmart Informationen**
    (`?area=informations`), Device Class `problem`, die Meldungstexte stehen
    im Attribut `meldungen`.
- **Aerosmart Wärmepumpe / Lüftung / Raumbediengerät**: eigene Geräte mit
  Seriennummer und Softwareversion, je Gerät
  - alle Werte des Statusbereichs als Sensor bzw. Binärsensor (Temperaturen,
    Drehzahlen, Relaiskontakte, Anforderungen, Betriebsstunden, …),
  - alle im Bereich „Betrieb“ änderbaren Einstellungen als Number, Select
    oder Switch (Kategorie *Konfiguration*), z. B. Smart-Grid-Modus,
    Heiz-/Kühlgrenze, Party-Dauer, CO₂-Zielwerte. Einstellungen, bei denen das
    Gerät neu startet, sind standardmäßig deaktiviert. Werks-Reset und
    „History löschen“ werden nie angeboten.

Werte, die schon durch die bisherigen Sensoren abgedeckt sind, werden je Gerät
deaktiviert angelegt. Melden mehrere Geräte denselben Parameter, verwenden die
bisherigen Sensoren den neuesten Wert (höchste `rowId`).

Schreiben erfolgt wie im Web-Interface per `POST <pfad>` mit
`[{"parameterId", "deviceId", "value"}]`; danach wartet die Integration bis zu
10 s, bis `?area=lastchanges` die Änderung bestätigt. Details zur API:
[docs/API.md](docs/API.md).

Pro Abfragezyklus werden `?area=values`, `?area=errors` und
`?area=informations` gelesen.

## Lizenz

[MIT](LICENSE) – freie Nutzung, Änderung und Weitergabe, Namensnennung und
Lizenztext müssen erhalten bleiben, keine Gewährleistung.
