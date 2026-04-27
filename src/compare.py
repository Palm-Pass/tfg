#!/usr/lib/howdy/.venv/bin/python

import asyncio
import os
import sys

from message_print import Printer, setup_runtime_environment, silence_warnings

setup_runtime_environment()
silence_warnings()

from howdy import paths_factory
from howdy import snapshot
from howdy import paths

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
