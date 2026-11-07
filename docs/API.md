# Fernwartungsmodul API (reverse-engineered)

Source: the psiio Angular web UI served at `http://<host>/home` (lighttpd,
bundle `main.8733be2f71060662.js`, Sept 2023). All findings below come from that
bundle plus live GET responses from a device with an RBG-TP, LU and WP.

## Transport

- Base URL is hard-coded in the UI: `<schema>//<host>:334`.
- Reads: `GET /dw?area=<area>`
- Writes: `POST /dw` with a JSON body.
- Headers sent by the UI: `Content-Type: application/json`, `Accept: application/json`.
- No authentication, no cookies, no CSRF token.
- Unknown areas return `{}` with HTTP 200 (as does `GET /dw` with no area).

## Common envelope

Almost every area returns a list of *environment* blocks:

```json
[{"key": 100, "identifier": "<guid>", "ticks": 639295205254201036, "value": [...]}]
```

- `key`: hardware environment (`100`, `200`, ...). A device belongs to
  environment `100 * trunc(hardwareId / 100)`.
- `identifier`: a new GUID on every response. `ticks` are .NET ticks.
- `value`: the area payload. For per-device areas it is a list of
  `{"hardwareId": 130, "hardwareEnvironment": 100, ...}` objects.

Exceptions: `languages` and `parameterDetails` are bare lists, and empty
areas return `[]`.

## Devices (`hardwareId`)

| id  | name   | `HARDWARE_TYPE` (1178) | role                              |
|-----|--------|------------------------|-----------------------------------|
| 120 | RBG-TP | 1                      | room control unit (touch panel)   |
| 130 | LU     | 4                      | ventilation unit                  |
| 140 | WP     | 5                      | heat pump                         |

## Read areas

| area                  | used by UI for                       | payload of `value[]`                                                      |
|-----------------------|--------------------------------------|---------------------------------------------------------------------------|
| `values`              | all live values                      | `{hardwareId, values:[{rowId, parameterId, currentValue, timeStamp}]}`    |
| `lastchanges`         | write confirmation                   | same shape as `values`                                                    |
| `restartValues`       | confirming device restart/ID change  | same shape, only parameters 1340, 1158, 7500                              |
| `hardware`            | device list                          | `{id, name, serialNumber, dnr, softwareversion, type, eType, hasWarning, warningCount, hasInformation, informationCount, hasTestMode, hasResetMode, hasHistoryMode, hardwareversions:[{name, parameterId}], ...}` |
| `hardwareEnvironment` | environment selector                 | `{hardwareEnvironment}` per device                                        |
| `hardwareeinzelraum`  | single-room control (psiioROOM)      | rooms with `features[]` (empty here)                                      |
| `options`             | parameter metadata + menus           | `{hardwareId, displays:[Feature]}` (≈290 KB)                              |
| `betriebsart`         | operating-mode selector              | `[Feature]` (param 5002 `E_MODUS_WLG`)                                    |
| `tempconfig`          | setpoint editor on dashboard         | `[Feature]` (5016 `E_RAUM_SOLL`, 5064 `E_T_BW_SOLL`)                      |
| `temperature`         | dashboard tiles                      | `{key, parameterId, temperature, unit, timeStamp, priority, roomNameId, roomValueId}` already scaled (e.g. 200 Raum 21.0 °C, 1054 Boiler 55.0 °C, 230 CO₂ 680 ppm) |
| `errors`              | active faults                        | `{hardwareId, parameterId, ...}`; UI text = language entry `name`, `units[index=1]` |
| `informations`        | active information messages          | same as `errors`                                                          |
| `icons`               | status icons in footer               | `{iconType, hardwareEnvironment, ...}`                                    |
| `history`             | fault history per device             | `{hardwareId, history:[{parameterId, date: DDMMYYYY, time: HHMMSS, error1, error2, error3}]}`; error columns are params 800, 7500, 7566 |
| `parameterDetails`    | detail requests                      | bare list `{requestParameter, parameterId, requestKey}`                   |
| `languages`           | all texts                            | bare list `{countryCode: DE/EN/FR/IT, parameter, parameterId, name, unitRaw, units:[{index, text}]}` (≈790 KB, 1194 params × 4 languages) |

`hardware`, `errors` and `icons` are flagged in the UI as areas that may carry
errors (`hasErrors`).

### Feature object (`options`, `betriebsart`, `tempconfig`)

```json
{"parameterId": 5064, "parameterName": "E_T_BW_SOLL", "hardwareId": 0,
 "hardwareEnvironment": 100, "minValue": 20000, "maxValue": 55000,
 "schritte": 1000, "divisor": 1000, "komma": 0, "einheit": "°C",
 "defaultValue": 47000, "countOptions": 0, "invalidOptionsIndex": [],
 "currentValue": null, "rowId": 0, "restarOnChange": false,
 "bereiche": [{"bereichBit": 33, "isDisplayEnabled": true, "isEditEnabled": true,
               "isResetEnabled": false, "isTestEnabled": false}]}
```

Feature type, derived in the UI: `countOptions > 2` → list, `countOptions` 1..2
→ bool, otherwise number. Option texts come from `languages[].units`.

`bereichBit` (menu area, enum `BED_PAR_*`): 0 Status, 3 Betrieb (user
settings), 6 Werk, 9 Setup, 12 Testmode, 15 Systemzeit, 18 Device-ID,
21 Automatik, 24 History, 27 Inbetriebnahme, 30 Multi-ID, 33 Temp-Config.

### Value scaling

```
display = trunc(raw / divisor) / 10**komma       # ql.GetValue
raw     = trunc(display * divisor) * 10**komma   # ql.GetRawValue
```

Examples: 5064 raw 48000, divisor 1000, komma 0 → 48 °C; 5186 raw 16000,
divisor 100, komma 1 → 16.0 °C. Temperatures in `values` are m°C (÷1000).

## Writes: `POST /dw`

```json
[{"parameterId": 5064, "deviceId": 140, "value": 48000}]
```

- Body is a list; several parameters can be sent at once.
- `value` is the raw integer (see scaling above).
- `deviceId` is a `hardwareId`, or for environment-wide settings (operating
  mode 5002, `tempconfig` setpoints) the environment key (e.g. `100`).
- The response is ignored. The UI confirms success by polling
  `area=lastchanges` once per second, up to 10 times, until the parameter
  shows a `rowId` greater than the one before the write (and, optionally,
  the expected `currentValue`).

Special writes the UI performs:

| parameterId | name             | value | effect                                      |
|-------------|------------------|-------|---------------------------------------------|
| 6000        | `E_DEFAULT`      | 1     | reset device to factory defaults            |
| 6002        | `E_CLEARHISTORY` | 1     | clear fault history                         |
| (list)      | history params   | 0     | "mass read": writing 0 requests a re-read   |
| any         | —                | `defaultValue` | per-parameter reset                |

Writes were **not** exercised against the device during this analysis.

### User-editable parameters (`bereichBit` 3, `isEditEnabled`)

Selection relevant for Home Assistant:

| dev | id   | name                      | range / options                              | div / komma |
|-----|------|---------------------------|----------------------------------------------|-------------|
| env | 5002 | Betriebsart `E_MODUS_WLG` | 0–3 Manuell Stufe 0–3, 4 Automatik, 5 Party (6 Ferien, 7 Reinigung exist, but the web UI only offers index < 6) | 1/0 |
| env | 5016 | Raum Soll `E_RAUM_SOLL`   | 14000–26000 step 100, °C                     | 100/1       |
| 140 | 5064 | Brauchwasser Soll         | 20000–55000 step 1000, °C                    | 1000/0      |
| 140 | 5624 | Modus Smart Grid          | kein; PV; Niedertarif; PV oder Niedertarif   | 1/0         |
| 140 | 5630 | Heizgrenztemperatur       | 10000–30000 step 500, °C                     | 100/1       |
| 140 | 5186 | Kühlgrenztemperatur       | 16000–30000 step 500, °C                     | 100/1       |
| 140 | 5510 | Heizungssperre Sommer     | Aus; Ein                                     | 1/0         |
| 140 | 5496 | HEIZUNG+ Sollwert-Erhöhung| 300–2000 step 100, K                         | 100/1       |
| 140 | 5494 | HEIZUNG+ Zeitspanne       | 1800–14400 step 60, min                      | 60/0        |
| 130 | 5038 | Party Zeitspanne          | 600–14400 step 600, min                      | 60/0        |
| 130 | 5060 | Soll-Volumenstrom Stufe 2 | 40–600, m³/h                                 | 1/0         |
| 130 | 5328 / 5330 | Absenkung Stufe 1 / Erhöhung Stufe 3 | %                       | 1/0         |
| 130 | 5026 | Volumenstrombalance       | -50–30, %                                    | 1/0         |
| 130 | 5274–5280 | CO₂-Zielwert Lüfterstufe 0–3 | ppm                                   | 1/0         |
| 120 | 5152 | Raumfühler Offset         | -10000–10000 step 100, K                     | 100/1       |

The full list (≈50 parameters, including installer-level ones) is in
`options` → `displays[]` with `bereiche[].bereichBit == 3 && isEditEnabled`.

Which device reports an environment parameter with the newest `rowId`
changes over time (5002 came from the RBG-TP in the morning, from the LU in
the evening), so it is not suitable for deciding where to show it.

## Merging values across devices

The same `parameterId` is reported by several devices, often with different
values (149 duplicates, 69 differing on the test device), e.g.:

| id   | 130 (LU)          | 140 (WP)           | 120 (RBG-TP)       |
|------|-------------------|--------------------|--------------------|
| 200  | 21166 @00:08      | 21166 @00:08       | 21038 @20:21       |
| 1054 | —                 | 55051 @16:28       | 51246 @00:08       |
| 1158 | 130204016         | 140201666          | 120200604          |

The UI (`getValuesByEnvironment`) resolves this by taking, per
`parameterId`, the entry with the **highest `rowId`** across devices, or
it reads a specific `hardwareId` directly. Device-specific parameters (serial
number, software version, history) must always be read per `hardwareId`.
