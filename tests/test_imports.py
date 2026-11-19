
import importlib


def test_app_package_import():
    module = importlib.import_module("app")
    assert module is not None
