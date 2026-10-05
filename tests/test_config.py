"""Check metadata against Supervisor's web UI URL contract."""

import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]

# Supervisor's ATTR_WEBUI validator requires both HOST and PORT placeholders.
# https://github.com/home-assistant/supervisor/blob/main/supervisor/apps/validate.py
# The resolver also requires the PORT placeholder, including with host_network.
# https://github.com/home-assistant/supervisor/blob/main/supervisor/apps/app.py
WEBUI_PATTERN = re.compile(
    r"^(?:https?|\[PROTO:\w+\]):\/\/\[HOST\]:\[PORT:\d+\].*$"
)


class MetadataTests(unittest.TestCase):
    def test_app_webui_passes_supervisor_validation(self):
        config = json.loads((ROOT / "rtl_433/config.json").read_text(encoding="utf-8"))
        self.assertRegex(config["webui"], WEBUI_PATTERN)

    def test_literal_port_regression_is_rejected(self):
        self.assertIsNone(WEBUI_PATTERN.match("http://[HOST]:8433"))


if __name__ == "__main__":
    unittest.main()
