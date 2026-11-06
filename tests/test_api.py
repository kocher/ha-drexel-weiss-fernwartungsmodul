"""Self-check for the pure helpers (run: python3 -m unittest discover -s tests)."""

from __future__ import annotations

import importlib.util
import pathlib
import unittest

# Load api.py directly: importing the package would drag in Home Assistant.
_SPEC = importlib.util.spec_from_file_location(
    "drexel_api",
    pathlib.Path(__file__).parents[1] / "custom_components" / "drexel" / "api.py",
)
api = importlib.util.module_from_spec(_SPEC)
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

    def test_parse_rejects_unknown_shape(self):
        with self.assertRaises(ValueError):
            api.parse_values({"foo": "bar"})

    def test_convert_value(self):
        self.assertEqual(api.convert_value(23456, scale=1000), 23.456)
        self.assertEqual(
            api.convert_value(8, states={8: "Wärmepumpe ein"}), "Wärmepumpe ein"
        )
        self.assertEqual(api.convert_value(99, states={8: "x"}), "Unbekannt")
        self.assertIsNone(api.convert_value(None))

    def test_build_url(self):
        self.assertEqual(
            api.build_url("192.168.1.2", 334), "http://192.168.1.2:334/dw?area=values"
        )


if __name__ == "__main__":
    unittest.main()
