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
hinzuzufügen, in `const.py` einen `SensorDef`/`BinarySensorDef` mit seiner
`parameter_id` ergänzen und neu starten.

Die Komponente liest `http://<host>:<port><pfad>?area=values` und ordnet
`payload[0]["value"][*]["values"][*]` zu `{parameterId: currentValue}` zu.

## Lizenz

[MIT](LICENSE) – freie Nutzung, Änderung und Weitergabe, Namensnennung und
Lizenztext müssen erhalten bleiben, keine Gewährleistung.
