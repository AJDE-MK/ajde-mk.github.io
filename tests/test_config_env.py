import importlib
import os
import unittest
from unittest import mock

import support  # noqa: F401
import config


class ConfigEnvTests(unittest.TestCase):
    def tearDown(self):
        importlib.reload(config)

    def test_base_path_and_form_key_default_to_empty(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MK_BASE_PATH", None)
            os.environ.pop("MK_FORM_KEY", None)
            importlib.reload(config)
        self.assertEqual(config.BASE_PATH, "")
        self.assertEqual(config.FORM_KEY, "")

    def test_base_path_comes_from_environment(self):
        with mock.patch.dict(os.environ, {"MK_BASE_PATH": "/my-repo"}):
            importlib.reload(config)
        self.assertEqual(config.BASE_PATH, "/my-repo")

    def test_base_path_trailing_slash_is_removed(self):
        with mock.patch.dict(os.environ, {"MK_BASE_PATH": "/my-repo/"}):
            importlib.reload(config)
        self.assertEqual(config.BASE_PATH, "/my-repo")

    def test_base_path_without_leading_slash_gets_one(self):
        with mock.patch.dict(os.environ, {"MK_BASE_PATH": "my-repo"}):
            importlib.reload(config)
        self.assertEqual(config.BASE_PATH, "/my-repo")

    def test_form_key_comes_from_environment(self):
        with mock.patch.dict(os.environ, {"MK_FORM_KEY": "abc-123"}):
            importlib.reload(config)
        self.assertEqual(config.FORM_KEY, "abc-123")


if __name__ == "__main__":
    unittest.main()
