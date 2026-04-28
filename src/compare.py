#!/usr/lib/howdy/.venv/bin/python

import asyncio
import os
import sys

from message_print import Printer, setup_runtime_environment, silence_warnings

setup_runtime_environment()
silence_warnings()

from howdy import paths_factory

paths_factory.config_file_path = lambda: os.environ.get("HOWDY_GESTURE_CONFIG", "/etc/howdy/config.ini")

from Authenticate import run_authenticator


if __name__ == "__main__":
    printer = Printer()
    printer.print_msg("Starting compare.py")
    printer.print_msg("Message from TFG Project")
    printer.print_msg("Loaded uv libraries correctly")
    asyncio.run(run_authenticator(printer))
