import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tournament.config import load_local_env


class ConfigTests(unittest.TestCase):
    def test_dotenv_loads_allowed_values_without_overriding_or_executing(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(os.environ, {"NOSANA_MODEL_ID": "existing"}, clear=True):
            p = Path(td) / ".env"
            p.write_text("export NOSANA_API_KEY='literal-$(no-execution)'\n"
                         "NOSANA_MODEL_ID=other\nNOSANA_API_BASE=https://inference.nosana.com/v1 # comment\n"
                         "UNRELATED_SETTING=ignored\n")
            load_local_env(p)
            self.assertEqual(os.environ["NOSANA_API_KEY"], "literal-$(no-execution)")
            self.assertEqual(os.environ["NOSANA_MODEL_ID"], "existing")
            self.assertNotIn("UNRELATED_SETTING", os.environ)
            self.assertEqual(os.environ["NOSANA_API_BASE"], "https://inference.nosana.com/v1")

    def test_bad_quote_error_does_not_echo_secret(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / ".env"
            p.write_text('NOSANA_API_KEY="example-sensitive-value\n')
            with self.assertRaisesRegex(ValueError, "line 1") as caught:
                load_local_env(p)
            self.assertNotIn("example-sensitive-value", str(caught.exception))
