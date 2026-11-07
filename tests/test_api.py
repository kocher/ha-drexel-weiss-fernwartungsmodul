"""Self-check for the pure helpers (run: python3 -m unittest discover -s tests)."""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

# Load api.py directly: importing the package would drag in Home Assistant.
_SPEC = importlib.util.spec_from_file_location(
    "drexel_api",
    pathlib.Path(__file__).parents[1] / "custom_components" / "drexel" / "api.py",
)
api = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = api  # dataclasses look the module up
_SPEC.loader.exec_module(api)

SAMPLE = [
    {
        "value": [
            {"values": [{"parameterId": 1184, "currentValue": 650}]},
            {
                "values": [
                    {"parameterId": 210, "currentValue": 23456},
                    {"parameterId": 1314, "currentValue": 8},
                ]
            },
        ]
    }
]


class TestApi(unittest.TestCase):
    def test_parse_flattens_groups(self):
        values = api.parse_values(SAMPLE)
        self.assertEqual(values[210], 23456)
        self.assertEqual(values[1184], 650)

    def test_parse_prefers_newest_row_across_devices(self):
        payload = [
            {
                "value": [
                    {
                        "hardwareId": 140,
                        "values": [{"rowId": 6465, "parameterId": 1054, "currentValue": 55051}],
                    },
                    {
                        "hardwareId": 120,
                        "values": [{"rowId": 247, "parameterId": 1054, "currentValue": 51246}],
                    },
                ]
            }
        ]
        self.assertEqual(api.parse_values(payload)[1054], 55051)

    def test_parse_rejects_unknown_shape(self):
        with self.assertRaises(ValueError):
            api.parse_values({"foo": "bar"})

    def test_build_url(self):
        self.assertEqual(
            api.build_url("192.168.1.2", 334), "http://192.168.1.2:334/dw?area=values"
        )
        self.assertEqual(
            api.build_url("192.168.1.2", 334, query=api.INFORMATIONS_QUERY),
            "http://192.168.1.2:334/dw?area=informations",
        )

    def test_normalize_host(self):
        for text, host in (
            ("192.168.169.41", "http://192.168.169.41"),
            (" http://192.168.169.41/home ", "http://192.168.169.41"),
            ("http://192.168.169.41:80/home", "http://192.168.169.41"),
            ("https://aerosmart.example.org/", "https://aerosmart.example.org"),
            ("aerosmart.local", "http://aerosmart.local"),
            ("fe80::1", "http://[fe80::1]"),
            ("", ""),
        ):
            self.assertEqual(api.normalize_host(text), host, text)
        self.assertEqual(
            api.build_url(api.normalize_host("http://192.168.169.41/home"), 334),
            "http://192.168.169.41:334/dw?area=values",
        )

    def test_has_informations(self):
        envelope = {"key": 100, "identifier": "abc", "ticks": 639288294421615703, "value": []}
        for empty in ({}, [], "", None, {"value": []}, [{"value": []}], [envelope]):
            self.assertFalse(api.has_informations(empty), empty)
        for filled in ({"value": [{"text": "Filter tauschen"}]}, [{"value": []}, {"x": 1}]):
            self.assertTrue(api.has_informations(filled), filled)


LANGUAGES = [
    {"countryCode": "DE", "parameterId": 5002, "name": "Betriebsart",
     "units": [{"index": i, "text": t} for i, t in enumerate(
         ["Manuell Stufe 0", "Manuell Stufe 1", "Automatikbetrieb", "Party",
          "x", "y", "Ferien", "Reinigung"])]},
    {"countryCode": "EN", "parameterId": 5002, "name": "Operating mode", "units": []},
    {"countryCode": "DE", "parameterId": 5016, "name": "Raum-Soll", "units": []},
    {"countryCode": "DE", "parameterId": 5510, "name": "Heizungssperre \\Sommer",
     "units": [{"index": 0, "text": "Aus"}, {"index": 1, "text": "Ein"}]},
    {"countryCode": "DE", "parameterId": 5500, "name": "Externer Kontakt WP",
     "units": [{"index": 0, "text": "EVU-Sperre"}, {"index": 1, "text": "Aus"}]},
    {"countryCode": "DE", "parameterId": 7500, "name": "Summenstörung 2",
     "units": [{"index": 0, "text": ""}, {"index": 1, "text": "Filter tauschen"}]},
    {"countryCode": "DE", "parameterId": 7002, "name": "Grobstaubfilter wechseln!",
     "units": [{"index": 0, "text": "Nein"}, {"index": 1, "text": "Ja"}]},
    {"countryCode": "DE", "parameterId": 5000, "name": "Gerätetyp",
     "units": [{"index": 5, "text": "aerosmart m"}]},
]


def _feature(parameter_id, name, bereiche, **extra):
    return {"parameterId": parameter_id, "parameterName": name,
            "bereiche": bereiche, "minValue": 0, "maxValue": 1, "schritte": 1,
            "divisor": 1, "komma": 0, "einheit": "", "invalidOptionsIndex": [],
            **extra}


STATUS = [{"bereichBit": 0, "isDisplayEnabled": True, "isEditEnabled": False}]
BETRIEB = [{"bereichBit": 3, "isDisplayEnabled": True, "isEditEnabled": True}]
WERK = [{"bereichBit": 6, "isDisplayEnabled": True, "isEditEnabled": True}]

OPTIONS = [{"key": 100, "value": [{"hardwareId": 140, "displays": [
    _feature(200, "T_RAUM", STATUS, divisor=100, komma=1, einheit="°C"),
    _feature(5510, "E_HEIZUNG_SPERRE_SOMMER", BETRIEB),
    _feature(5500, "E_EXT_WP_OPT", BETRIEB, maxValue=2, invalidOptionsIndex=[0, 1, 2]),
    _feature(5016, "E_RAUM_SOLL", STATUS),
    _feature(9999, "E_WERK", WERK),
    _feature(6000, "E_DEFAULT", BETRIEB),
]}]}]

BETRIEBSART = [{"key": 100, "value": [_feature(
    5002, "E_MODUS_WLG", [], hardwareEnvironment=100, maxValue=7,
    invalidOptionsIndex=[1])]}]
TEMPCONFIG = [{"key": 100, "value": [_feature(
    5016, "E_RAUM_SOLL", [], hardwareEnvironment=100, minValue=14000,
    maxValue=26000, schritte=100, divisor=100, komma=1, einheit="°C")]}]


class TestMetadata(unittest.TestCase):
    def setUp(self):
        self.texts = api.index_languages(LANGUAGES, "EN")
        self.owners = {5002: 120, 5016: 120, 1054: 140}
        self.parameters = {
            (p.hardware_id, p.parameter_id): p
            for p in api.build_parameters(
                OPTIONS, [BETRIEBSART, TEMPCONFIG], self.texts, self.owners
            )
        }

    def test_language_fallback_and_cleanup(self):
        self.assertEqual(api.language_code("en-GB"), "EN")
        self.assertEqual(api.language_code("nl"), "DE")
        self.assertEqual(self.texts[5002].name, "Operating mode")
        self.assertEqual(self.texts[5016].name, "Raum-Soll")
        self.assertEqual(self.texts[5510].name, "Heizungssperre Sommer")

    def test_selection(self):
        self.assertEqual(
            set(self.parameters),
            {
                (100, 5002), (100, 5016), (140, 200), (140, 5510), (140, 5500),
                (140, 5016), (140, 1054),
            },
        )
        self.assertTrue(self.parameters[(100, 5016)].environment)
        self.assertFalse(self.parameters[(140, 200)].writable)

    def test_devices(self):
        # Environment controls go to the device that reports them.
        self.assertEqual(self.parameters[(100, 5002)].device_id, 120)
        self.assertEqual(self.parameters[(140, 200)].device_id, 140)
        # A per-device copy of an environment control stays read only.
        self.assertFalse(self.parameters[(140, 5016)].writable)

    def test_extra_parameters(self):
        boiler = self.parameters[(140, 1054)]
        self.assertEqual(boiler.key, "T_BOILER")
        self.assertFalse(boiler.writable)
        self.assertAlmostEqual(boiler.to_native(55051), 55.051)
        without_owner = api.build_parameters(OPTIONS, [], self.texts, {})
        self.assertNotIn(1054, [p.parameter_id for p in without_owner])

    def test_writable_options(self):
        mode = self.parameters[(100, 5002)]
        self.assertEqual(
            mode.options,
            {0: "Manuell Stufe 0", 2: "Automatikbetrieb", 3: "Party", 4: "x", 5: "y"},
        )
        self.assertTrue(self.parameters[(140, 5510)].is_binary)
        external = self.parameters[(140, 5500)]
        self.assertFalse(external.writable)
        self.assertEqual(external.options, {0: "EVU-Sperre", 1: "Aus"})

    def test_hidden_options(self):
        # Ferien/Reinigung are not offered, like in the web UI ...
        mode = self.parameters[(100, 5002)]
        self.assertNotIn(6, mode.options)
        self.assertNotIn(7, mode.options)
        self.assertEqual(mode.choices(2), mode.options)
        # ... but shown while active (set on the room panel).
        self.assertEqual(mode.option_text(6), "Ferien")
        self.assertEqual(mode.choices(6), {**mode.options, 6: "Ferien"})
        self.assertEqual(mode.choices(None), mode.options)
        self.assertEqual(mode.choices(99), mode.options)

    def test_scaling(self):
        setpoint = self.parameters[(100, 5016)]
        self.assertEqual(setpoint.to_native(21000), 21.0)
        self.assertEqual(setpoint.to_native(setpoint.step), 0.1)
        self.assertEqual(setpoint.to_raw(21.5), 21500)
        self.assertEqual(setpoint.to_raw(21.53), 21500)
        self.assertEqual(setpoint.to_raw(99), 26000)
        self.assertAlmostEqual(self.parameters[(140, 200)].to_native(21166), 21.166)

    def test_hardware(self):
        payload = [{"key": 100, "value": [
            {"id": 140, "name": "WP", "eType": 5, "serialNumber": "140201666",
             "softwareversion": "401440"},
            {"id": 120, "name": "RBG-TP", "eType": -1, "serialNumber": "",
             "softwareversion": "401441"},
        ]}]
        wp, rbg = api.parse_hardware(payload, api.index_languages(LANGUAGES, "DE"))
        self.assertEqual(wp.model, "aerosmart m WP")
        self.assertEqual(rbg.model, "RBG-TP")
        self.assertIsNone(rbg.serial_number)

    def test_messages(self):
        payload = [{"key": 100, "value": [{"hardwareId": 130, "parameterId": 7500}]}]
        (message,) = api.parse_messages(payload, self.texts)
        self.assertEqual(message.hardware_id, 130)
        self.assertEqual(message.text, "Summenstörung 2")
        self.assertEqual(api.parse_messages([], self.texts), [])
        self.assertEqual(api.parse_messages({}, self.texts), [])

    def test_real_informations_response(self):
        # GET ?area=informations while the coarse filter was due.
        payload = [{"key": 100, "identifier": "fd3ab24d3e104432bc97360ba2e23997",
                    "value": [{"hardwareId": 130, "parameterId": 7002, "text": None,
                               "valueText": None, "hardwareEnvironment": 100}],
                    "ticks": 639288294421615703}]
        self.assertTrue(api.has_informations(payload))
        self.assertEqual(
            api.parse_messages(payload, self.texts),
            [api.Message(130, 7002, "Grobstaubfilter wechseln!")],
        )


class TestClimate(unittest.TestCase):
    def test_room_action(self):
        self.assertIsNone(api.room_action(None))
        self.assertEqual(api.room_action(0), "idle")  # Aus
        self.assertEqual(api.room_action(2), "idle")  # Boilerladung
        self.assertEqual(api.room_action(7), "heating")  # Niedertemperaturheizung
        self.assertEqual(api.room_action(11), "cooling")  # Aktive Kühlung


class TestDeviceValues(unittest.TestCase):
    PAYLOAD = [{"key": 100, "value": [
        {"hardwareId": 140, "values": [
            {"rowId": 6465, "parameterId": 1054, "currentValue": 55051}]},
        {"hardwareId": 120, "values": [
            {"rowId": 247, "parameterId": 1054, "currentValue": 51246}]},
    ]}]

    def test_per_device(self):
        self.assertEqual(
            api.parse_device_values(self.PAYLOAD),
            {140: {1054: 55051}, 120: {1054: 51246}},
        )

    def test_newest_owners(self):
        self.assertEqual(api.newest_owners(self.PAYLOAD), {1054: 140})
        self.assertEqual(api.newest_owners({}), {})

    def test_parameter_owners(self):
        payload = [{"key": 100, "value": [
            {"hardwareId": 130, "values": [
                {"rowId": 8567, "parameterId": 5002, "currentValue": 2},
                {"rowId": 900, "parameterId": 200, "currentValue": 21166}]},
            {"hardwareId": 120, "values": [
                {"rowId": 49, "parameterId": 5002, "currentValue": 2},
                {"rowId": 950, "parameterId": 1054, "currentValue": 51246},
                {"rowId": 100, "parameterId": 200, "currentValue": 21038}]},
            {"hardwareId": 140, "values": [
                {"rowId": 600, "parameterId": 1054, "currentValue": 55051}]},
        ]}]
        hardware = [
            api.Hardware(120, "RBG-TP", "RBG-TP", None, None),
            api.Hardware(130, "LU", "LU", None, None),
            api.Hardware(140, "WP", "WP", None, None),
        ]
        owners = api.parameter_owners(payload, hardware)
        # fixed placement even though another device has the newest value
        self.assertEqual(owners[5002], 120)
        self.assertEqual(owners[1054], 140)
        # everything else: newest value
        self.assertEqual(owners[200], 130)
        # no room panel: fall back to the newest value
        self.assertEqual(api.parameter_owners(payload, hardware[1:])[5002], 130)

    def test_newest_row(self):
        self.assertEqual(api.newest_row(self.PAYLOAD, 1054), 6465)
        self.assertEqual(api.newest_row(self.PAYLOAD, 1054, 120), 247)
        self.assertEqual(api.newest_row(self.PAYLOAD, 1), -1)

    def test_write_body(self):
        self.assertEqual(
            api.write_body(5064, 100, 48000),
            [{"parameterId": 5064, "deviceId": 100, "value": 48000}],
        )


if __name__ == "__main__":
    unittest.main()
