# Drexel und Weiss Aerosmart für Home Assistant

Bindet eine **Drexel und Weiss Aerosmart** (Lüftung mit Wärmepumpe) über ihr
**Fernwartungsmodul** in Home Assistant ein. Die Integration zeigt alles, was
das Web-Interface des Moduls (`http://<modul>/home`) anzeigt, und kann dieselben
Einstellungen ändern – Betriebsart, Raum- und Brauchwasser-Solltemperatur und
die Einstellungen der einzelnen Geräte.

Die Verbindung läuft lokal über die Daten-Schnittstelle des Moduls, ohne Cloud
und ohne Zugangsdaten.

## Was du bekommst

Die Integration liest beim Start, welche Geräte am Modul hängen und welche
Werte sie haben, und legt die Entitäten daraus an – mit den Namen, Einheiten,
Wertebereichen und Auswahltexten des Moduls, in der Sprache von Home Assistant
(Deutsch, Englisch, Französisch oder Italienisch).

**Raumtemperatur (Climate „Raum“)** – Thermostat für die Karte und für
Sprachassistenten:

- Raumtemperatur und Raum-Soll (14–26 °C)
- Betriebsart als Preset: Manuell Stufe 0–3, Automatikbetrieb, Party
- zeigt an, ob die Wärmepumpe gerade heizt, kühlt oder ruht

**Brauchwasser (Water Heater)**: Boilertemperatur und Brauchwasser-Soll
(20–55 °C).

**Je Gerät** (Wärmepumpe, Lüftung, Raumbediengerät – mit Seriennummer und
Softwareversion):

- alle Statuswerte als Sensoren: Temperaturen (Raum, Boiler, Warmwasserspeicher,
  Verdampfer, …), CO₂, Ventilatordrehzahlen, Betriebsstunden, Status der
  Wärmepumpe
- Relaiskontakte und Anforderungen (Heizstufen, Brauchwasser,
  Elektroheizstab, …) als Binärsensoren
- alle Einstellungen, die das Web-Interface im Bereich „Betrieb“ ändern lässt,
  als Number, Select oder Switch, z. B. Smart-Grid-Modus, Heiz- und
  Kühlgrenze, HEIZUNG+, Party-Dauer, Volumenstrom, CO₂-Zielwerte,
  Hintergrundbeleuchtung des Raumbediengeräts

**Meldungen** (am Fernwartungsmodul):

| Entität | bedeutet | Beispiele |
|---|---|---|
| **Störung** | etwas ist defekt oder außerhalb des zulässigen Bereichs; das Gerät schränkt den Betrieb ein oder schaltet ab | Fühlerstörung, Ventilator, Hoch-/Niederdruck, Kompressor |
| **Informationen** | Wartungshinweis, das Gerät läuft weiter | Grobstaubfilter wechseln!, Feinstaubfilter wechseln!, Kältemittelmangel |

Beide sind „an“, solange eine Meldung ansteht. Das Attribut `meldungen` listet
sie als `"<Gerät>: <Text>"`, z. B. `Lüftung: Grobstaubfilter wechseln!` – damit
lassen sich gezielt Benachrichtigungen bauen.

## Installation

**Über HACS:** HACS → ⋮ → *Benutzerdefinierte Repositories* →
`https://github.com/kocher/ha-drexel-weiss-fernwartungsmodul`, Typ
*Integration* → installieren → Home Assistant neu starten.

**Manuell:** `custom_components/drexel` nach `<config>/custom_components/drexel`
kopieren und Home Assistant neu starten.

Voraussetzung: Home Assistant 2024.8 oder neuer.

## Einrichten

Einstellungen → Geräte & Dienste → *Integration hinzufügen* → **Drexel und
Weiss Aerosmart**:

- **Host**: IP-Adresse oder Hostname des Fernwartungsmoduls. Die Adresse, unter
  der du das Web-Interface öffnest (`http://192.168.1.50/home`), geht auch.
- **Abfrageintervall**: wie oft Werte und Meldungen gelesen werden, Standard
  60 s (10–3600 s, später über *Konfigurieren* änderbar).
- **Erweitert** (eingeklappt): Port `334` und Pfad `/dw` der
  Daten-Schnittstelle. Das Web-Interface verwendet fest diese Werte; ändern
  musst du sie nur hinter einer Portweiterleitung oder einem Reverse-Proxy.

## Gut zu wissen

- **Änderungen** werden wie im Web-Interface an das Modul geschickt. Die
  Integration wartet bis zu 10 s, bis das Modul die Änderung bestätigt, erst
  dann zeigt Home Assistant den neuen Wert.
- **Einstellungen, bei denen ein Gerät neu startet**, sind standardmäßig
  deaktiviert und müssen bei Bedarf einzeln aktiviert werden.
- **Werks-Reset und „History löschen“** werden bewusst nicht angeboten.
- **Heizung aus** gibt es nicht: Das Gerät hat keinen Heizungs-Ausschalter,
  der Climate kennt deshalb nur „Heizen“.
- **Ferien und Reinigung** kann man – wie im Web-Interface – nicht auswählen.
  Sind sie am Raumbediengerät gesetzt, zeigt Home Assistant sie trotzdem an.
- **Werte, die das Modul nicht liefert** (z. B. für nicht vorhandene
  Funktionen wie Heizstufe 2), zeigt Home Assistant wie das Web-Interface als 0.

## PV-Überschuss nutzen (Blueprint)

Ohne SG-Box kann Home Assistant deren Smart-Grid-Funktion übernehmen: Das
Blueprint **Aerosmart PV-Überschuss** hebt bei Einspeisung über der
Leistungsaufnahme der Wärmepumpe plus einer Mindest-Einspeisung die Sollwerte
an und setzt sie danach zurück – wie die SG-Box, aber mit einem Netz- oder
Einspeise-Sensor statt dem Kontakt des Wechselrichters.

[![Blueprint importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fkocher%2Fha-drexel-weiss-fernwartungsmodul%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fdrexel%2Fpv_ueberschuss.yaml)

- **Leistungsaufnahme Wärmepumpe und Mindest-Einspeisung**: angehoben wird,
  wenn die Einspeisung für die Einschaltverzögerung über beiden zusammen liegt
  (Vorgabe 500 + 300 W), zurückgesetzt, wenn sie für die Ausschaltverzögerung
  unter der Mindest-Einspeisung liegt – so schaltet die Anhebung nicht ab,
  sobald die Wärmepumpe den Überschuss selbst verbraucht. Ob die Wärmepumpe
  läuft, wird nicht geprüft.
- Kühlt der Speicher während eines Überschusses ab, wird eine Bedingung
  erfüllt oder startet Home Assistant neu, wird ebenfalls erst nach der
  Einschaltverzögerung angehoben. Alle 10 Minuten prüft das Blueprint, ob
  etwas anzuheben ist, das bisher zurückgehalten wurde.
- **Brauchwasser**: Ist der Warmwasserspeicher kälter als 52 °C, wird
  Brauchwasser-Soll auf 55 °C gesetzt (beides einstellbar). Gemessen wird wie
  bei der SG-Box am Fühler der Wärmepumpe („Warmwasserspeicher WP“), nicht am
  Boiler-Fühler oben im Speicher, den das Web-Interface anzeigt. Über
  „Speicherfühler“ lässt sich ein anderer Sensor wählen.
- **Raum** (optional): Raum-Soll wird um 0,5–3 K angehoben – je nach „Modus
  Smart Grid“ bei PV, Niedertarif oder beidem, wie bei der SG-Box. Auf Wunsch
  nur unter eigenen Bedingungen (z. B. Heizperiode, Außentemperatur).
- **Zusätzliche Bedingungen** (optional): nur anheben, wenn z. B. die Fenster
  geschlossen sind oder jemand zu Hause ist. Das Zurücksetzen prüft sie nicht,
  eine Anhebung wird also immer beendet.
- **Niedertarif** (optional): ein Schalter oder Binärsensor, der Raum-Soll
  wie bei Überschuss anhebt. Brauchwasser bleibt wie bei der SG-Box
  unverändert – die Wärmepumpe lädt ohnehin selbst.
- Ein- und Ausschaltverzögerung (Standard 5 / 15 min) und eine Mindestdauer
  der Anhebung (Standard 30 min) verhindern Hin- und Herschalten bei Wolken.
  Hat jemand den Sollwert während der Anhebung geändert, bleibt dessen Wert
  stehen.
- **Ausfälle**: Liefert der Einspeise-Sensor keinen Wert, wird weder angehoben
  noch zurückgesetzt. Ist das Modul beim Zurücksetzen nicht erreichbar, wird
  das nachgeholt, sobald es wieder antwortet.
- **Benachrichtigung**: beim Anheben und Zurücksetzen, mit Einspeisung,
  aktueller Temperatur und Sollwerten, z. B. „Einspeisung 2480 W.
  Brauchwasser 45,0 °C, Soll 48,0 → 55,0 °C.“ Vorbelegt ist eine
  Benachrichtigung in Home Assistant; die Aktion lässt sich wie in jeder
  Automation auswählen (z. B. das Telefon) oder löschen.
- Als Sensor eignet sich ein Einspeise-Sensor (Einspeisung positiv) oder ein
  Netz-Sensor, bei dem Einspeisung negativ ist – im Blueprint auswählbar.

Die vorherigen Sollwerte merkt sich das Blueprint in Zahlenwert-Helfern
(Minimum 0, Maximum 100, Schrittweite 0,1), damit sie einen Neustart
überstehen – je einen für Brauchwasser und Raum vorher anlegen.

## Benachrichtigung bei Störungen und Informationen (Blueprint)

Das Blueprint **Aerosmart Meldungen** schickt eine Nachricht, sobald die
Aerosmart eine Störung oder Information meldet, und optional, wenn sie behoben
ist. Störung und Informationen lassen sich in einer Automation zusammen
überwachen.

[![Blueprint importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fkocher%2Fha-drexel-weiss-fernwartungsmodul%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fdrexel%2Fmeldungen.yaml)

- Titel „Aerosmart: Störung“ bzw. „Aerosmart: Informationen“, Nachricht z. B. „Lüftung:
  Grobstaubfilter wechseln!“, bei Behebung „Behoben: …“.
- Kommt zu einer anstehenden Meldung eine weitere hinzu, wird nur die neue
  gemeldet.
- Ein Neustart von Home Assistant oder ein kurzer Verbindungsabbruch zum Modul
  löst keine Nachricht aus.
- Vorbelegt ist eine Benachrichtigung in Home Assistant; die Aktion lässt sich
  wie in jeder Automation auswählen (z. B. das Telefon). Titel und Nachricht
  stehen als `{{ title }}` und `{{ message }}` bereit.

## Technik

Pro Abfrageintervall liest die Integration drei Bereiche des Moduls (`values`,
`errors`, `informations`); Texte, Geräte und Metadaten nur beim Start.
Die Schnittstelle ist in [docs/API.md](docs/API.md) beschrieben. Fehlt ein
Wert, den das Modul liefert, aber in keinem Menü zeigt, lässt er sich in
`api.py` unter `EXTRA_PARAMETERS` ergänzen.

## Lizenz

[MIT](LICENSE) – freie Nutzung, Änderung und Weitergabe, Namensnennung und
Lizenztext müssen erhalten bleiben, keine Gewährleistung.
