from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Optional

DEFAULT_APPNAME = "palm_pass_hints"
DEFAULT_TITLE = "Howdy TFG"
DEFAULT_ICON = "security-high"
DEFAULT_TIMEOUT = 5000
DEFAULT_GESTURE = "rock"

_EXTERNAL_MODULE: ModuleType | None = None


def _load_external_module() -> ModuleType:
	global _EXTERNAL_MODULE
	if _EXTERNAL_MODULE is not None:
		return _EXTERNAL_MODULE

	distribution = importlib.metadata.distribution("dbus-notification")
	module_path = Path(distribution.locate_file("dbus_notification/__init__.py"))
	if module_path.resolve() == Path(__file__).resolve():
		raise RuntimeError("The local dbus_notification.py is shadowing the installed dbus_notification package")

	spec = importlib.util.spec_from_file_location("_dbus_notification_external", module_path)
	if spec is None or spec.loader is None:
		raise RuntimeError("Could not load the installed dbus_notification package")

	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	_EXTERNAL_MODULE = module
	return module


def build_gesture_hint_message(target_gesture: str, gesture_only: bool) -> str:
	gesture = (target_gesture or DEFAULT_GESTURE).strip() or DEFAULT_GESTURE
	if gesture_only:
		return f"Gesture-only mode active. Perform: {gesture}"
	return f"Perform gesture: {gesture}"


def send_notification(
	message: str,
	title: str = DEFAULT_TITLE,
	appname: str = DEFAULT_APPNAME,
	icon: str = DEFAULT_ICON,
	timeout: int = DEFAULT_TIMEOUT,
	urgency: Optional[int] = None,
) -> int:
	external_module = _load_external_module()
	dbus_app = external_module.DBusNotification(appname=appname)
	return dbus_app.send(
		title=title,
		message=message,
		logo=icon,
		urgency=urgency,
		timeout=timeout,
	)


def notify_gesture_hint(target_gesture: str, gesture_only: bool = True) -> int:
	return send_notification(
		build_gesture_hint_message(target_gesture, gesture_only),
		title=DEFAULT_TITLE,
		appname=DEFAULT_APPNAME,
		icon=DEFAULT_ICON,
		timeout=DEFAULT_TIMEOUT,
	)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Send a desktop notification through D-Bus")
	parser.add_argument("--title", default=DEFAULT_TITLE, help="Notification title")
	parser.add_argument("--message", default=None, help="Notification body")
	parser.add_argument("--appname", default=DEFAULT_APPNAME, help="Application name shown by the notification daemon")
	parser.add_argument("--icon", default=DEFAULT_ICON, help="Notification icon")
	parser.add_argument("--timeout", default=DEFAULT_TIMEOUT, type=int, help="Timeout in milliseconds")
	parser.add_argument("--urgency", default=None, type=int, choices=[0, 1, 2], help="Urgency level")
	parser.add_argument("--gesture", default=DEFAULT_GESTURE, help="Gesture name to display when no message is provided")
	parser.add_argument("--gesture-only", action="store_true", help="Show the gesture-only hint text")
	return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
	args = parse_args(argv)
	message = args.message
	if message is None:
		message = build_gesture_hint_message(args.gesture, args.gesture_only)

	try:
		send_notification(
			message,
			title=args.title,
			appname=args.appname,
			icon=args.icon,
			timeout=args.timeout,
			urgency=args.urgency,
		)
		return 0
	except Exception as exc:
		print(f"ERROR: could not send DBus notification: {exc}", file=sys.stderr)
		return 1


if __name__ == "__main__":
	raise SystemExit(main())
