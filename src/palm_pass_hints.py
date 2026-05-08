

from __future__ import annotations

import configparser
import os
import sys
from typing import Tuple

from dbus_notification import build_gesture_hint_message, notify_gesture_hint

CONFIG_PATH = os.environ.get("HOWDY_GESTURE_CONFIG", "/etc/howdy/config.ini")


def load_gesture_settings(config_path: str = CONFIG_PATH) -> Tuple[str, bool]:
	parser = configparser.ConfigParser()
	parser.read(config_path)

	target_gesture = parser.get("gestures", "target_gesture", fallback="rock").strip() or "rock"
	gesture_only = parser.getboolean("gesture-only", "gesture-only", fallback=False)
	return target_gesture, gesture_only


def get_gesture_hint_string(gesture_only: bool = True) -> str:
	"""Get the gesture hint string based on current configuration."""
	try:
		target_gesture, _ = load_gesture_settings()
		return build_gesture_hint_message(target_gesture, gesture_only=gesture_only)
	except Exception:
		return build_gesture_hint_message("rock", gesture_only=gesture_only)


def main():
	try:
		target_gesture, gesture_only = load_gesture_settings()
		if not gesture_only:
			# The hint notification is intentionally shown as a gesture-only reminder.
			gesture_only = True

		notify_gesture_hint(target_gesture, gesture_only=gesture_only)
		return 0
	except Exception as exc:
		print(f"ERROR: could not show gesture hint: {exc}", file=sys.stderr)
		return 1


if __name__ == "__main__":
	raise SystemExit(main())
