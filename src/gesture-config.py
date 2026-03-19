import sys
import configparser
import os

#TODO: Add command to howdy and check security permissions for config file before writing to it.
CONFIG_PATH = "/etc/howdy/config.ini" 

VALID_GESTURES = ["None", "Rock", "Paper", "Scissors"]

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
        print("Usage: sudo python gesture-config.py [Gesture]")
        print(f"Example: sudo python gesture-config.py Rock")
    else:
        update_gesture(sys.argv[1])