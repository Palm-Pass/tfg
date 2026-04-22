#!/usr/lib/howdy/.venv/bin/python

import asyncio
import os
import sys

from message_print import Printer, setup_runtime_environment, silence_warnings

setup_runtime_environment()
silence_warnings()

DEFAULT_PROJECT_ROOT = "/usr/lib/howdy"
PROJECT_ROOT = os.path.realpath(os.environ.get("HOWDY_GESTURE_ROOT", DEFAULT_PROJECT_ROOT))
HOWDY_CORE_SRC = PROJECT_ROOT
HOWDY_BASE = PROJECT_ROOT

sys.path.insert(0, HOWDY_CORE_SRC)
sys.path.insert(1, HOWDY_BASE)

try:
    import paths
except ModuleNotFoundError:
    import types
    from pathlib import PurePath

    paths = types.ModuleType("paths")
    paths.config_dir = PurePath("/etc/howdy")
    paths.dlib_data_dir = PurePath("/usr/share/dlib-data")
    paths.user_models_dir = PurePath("/etc/howdy/models")
    paths.log_path = PurePath("/var/log/howdy")
    paths.data_dir = PurePath("/usr/share/howdy")
    sys.modules["paths"] = paths

import paths_factory
import snapshot

paths_factory.config_file_path = lambda: os.environ.get("HOWDY_GESTURE_CONFIG", "/etc/howdy/config.ini")
paths_factory.dlib_data_dir_path = lambda: "/usr/share/dlib-data"
paths_factory.user_model_path = lambda user: f"/etc/howdy/models/{user}.dat"
snapshot.data_path = "/usr/share/howdy"

from Authenticate import run_authenticator


if __name__ == "__main__":
    printer = Printer()
    printer.print_msg("Starting compare.py")
    printer.print_msg("Message from TFG Project")
    printer.print_msg("Loaded uv libraries correctly")
    asyncio.run(run_authenticator(printer))
