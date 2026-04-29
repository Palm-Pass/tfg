#!/usr/bin/env python3

import sys
import configparser
import os

CONFIG_PATH = os.environ.get("HOWDY_GESTURE_CONFIG", "/etc/howdy/config.ini")

VALID_CONFIG_VALUES = ["true", "false"]


def update_config(new_value):
    if new_value not in VALID_CONFIG_VALUES:
        print(f"ERROR: '{new_value}' is not a valid value.")
        print(f"Available options: {', '.join(VALID_CONFIG_VALUES)}")
        return

    config = configparser.ConfigParser()

    if not os.path.exists(CONFIG_PATH):
        print(f"ERROR: File not found at {CONFIG_PATH}")
        return

    config.read(CONFIG_PATH)

    if "gestures" not in config:
        config.add_section("gestures")

    config.set("gestures", "gesture_only", new_value)

    try:
        with open(CONFIG_PATH, "w") as configfile:
            config.write(configfile)
        print(f"Gesture-only mode set to {new_value}")
    except PermissionError:
        print("ERROR: You need to run this with 'sudo' to modify the config.ini")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: howdy-gesture-only [true/false]")
        print("Example: howdy-gesture-only true")
    else:
        update_config(sys.argv[1])
