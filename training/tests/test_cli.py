import builtins
import json
from contextlib import redirect_stdout
from io import StringIO
from unittest import TestCase
from unittest.mock import patch

from plex_training.cli import main


class CliTests(TestCase):
    def test_environment_reports_torch_import_failure_as_json(self) -> None:
        original_import = builtins.__import__

        def block_telemetry(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "telemetry" and level == 1 and (globals or {}).get("__package__") == "plex_training":
                raise OSError("[WinError 4551] Application Control blocked shm.dll")
            return original_import(name, globals, locals, fromlist, level)

        output = StringIO()
        with patch("builtins.__import__", side_effect=block_telemetry), redirect_stdout(output):
            status = main(["environment"])

        self.assertEqual(status, 2)
        report = json.loads(output.getvalue())
        self.assertEqual(report["torchVersion"], "unavailable")
        self.assertIn("WinError 4551", report["torchImportError"])

