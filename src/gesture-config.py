#!/usr/bin/env python3.10

import sys
import configparser
import os

PROJECT_ROOT = os.environ.get("HOWDY_GESTURE_ROOT", "/usr/lib/howdy-gesture")
CONFIG_PATH = os.environ.get("HOWDY_GESTURE_CONFIG", f"{PROJECT_ROOT}/config/config.ini")

VALID_GESTURES = ["None", "rock", "paper", "scissors"]

def update_gesture(new_gesture):
    if new_gesture not in VALID_GESTURES:
        print(f"ERROR: '{new_gesture}' is not a valid gesture.")
        print(f"Available options: {', '.join(VALID_GESTURES)}")
        return

    config = configparser.ConfigParser()
    
    if not os.path.exists(CONFIG_PATH):
        print(f"ERROR: File not found at {CONFIG_PATH}")
        return

    config.read(CONFIG_PATH)

    if 'gestures' not in config:
        config.add_section('gestures')
    
    config.set('gestures', 'target_gesture', new_gesture)

    try:
        with open(CONFIG_PATH, 'w') as configfile:
            config.write(configfile)
        print(f"Gesture changed to {new_gesture}")
    except PermissionError:
        print("ERROR: You need to run this with 'sudo' to modify the config.ini")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: sudo howdy gesture-config [Gesture]")
        print(f"Example: sudo howdy gesture-config Rock")
    else:
        update_gesture(sys.argv[1])