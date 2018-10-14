import os

from molten.contrib.toml_settings import TOMLSettings

from .common import path_to

ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")
SETTINGS = TOMLSettings.from_path(path_to("settings.toml"), ENVIRONMENT)

# TODO: Janky af!!
SETTINGS["database_engine_dsn"] = os.getenv("DATABASE_URL", SETTINGS["database_engine_dsn"])
SETTINGS["sessions"]["signing_key"] = os.getenv("SIGNING_KEY", "")


def __getattr__(name):
    return getattr(SETTINGS, name)
