#!/usr/lib/howdy/.venv/bin/python3

import json
import os
import subprocess
import sys
import time

from message_print import Printer, setup_runtime_environment, silence_warnings

setup_runtime_environment()
silence_warnings()

from howdy import paths_factory

paths_factory.config_file_path = lambda: os.environ.get("HOWDY_GESTURE_CONFIG", "/etc/howdy/config.ini")

import cv2
import dlib
from howdy.i18n import _
from howdy.recorders.video_capture import VideoCapture

from Config import Config
from Authenticate import Authenticator
import palm_pass_authenticator


def _mediapipe_available():
    result = subprocess.run(
        [sys.executable, "-c", "import mediapipe"],
        capture_output=True,
        timeout=10,
    )
    return result.returncode == 0


def init_gesture_recognizer(printer):
    if not _mediapipe_available():
        printer.print_msg("MediaPipe unavailable, gesture recognition disabled")
        return None, None

    try:
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision

        model_path = "/usr/lib/howdy/models/gesture_recognizer.task"
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.GestureRecognizerOptions(base_options=base_options)
        recognizer = vision.GestureRecognizer.create_from_options(options)
        printer.print_msg("Gesture recognizer initialized")
        return mp, recognizer
    except ImportError:
        return None, None


def init_face_detector(config, printer):
    if not os.path.isfile(paths_factory.shape_predictor_5_face_landmarks_path()):
        print(_("Data files have not been downloaded, please run the following commands:"))
        print("\n\tcd " + paths_factory.dlib_data_dir_path())
        print("\tsudo ./install.sh\n")
        sys.exit(1)

    if config.use_cnn:
        printer.print_msg("Using CNN face detector")
        face_detector = dlib.cnn_face_detection_model_v1(paths_factory.mmod_human_face_detector_path())
    else:
        printer.print_msg("Using HOG face detector")
        face_detector = dlib.get_frontal_face_detector()

    pose_predictor = dlib.shape_predictor(paths_factory.shape_predictor_5_face_landmarks_path())
    face_encoder = dlib.face_recognition_model_v1(paths_factory.dlib_face_recognition_resnet_model_v1_path())
    printer.print_msg("Face detection models initialized")
    return face_detector, pose_predictor, face_encoder


def load_face_models(user, printer):
    printer.print_msg(f"Loading face models for user: {user}")
    try:
        models = json.load(open(paths_factory.user_model_path(user)))
    except FileNotFoundError:
        sys.exit(10)

    if len(models) < 1:
        sys.exit(10)

    encodings = []
    for model in models:
        encodings += model["data"]

    printer.print_msg(f"Loaded {len(models)} face model(s)")
    return models, encodings


def init_video_capture(config, printer):
    device_path = config.parser.get("video", "device_path", fallback="NOT FOUND")
    printer.print_msg(f"Initializing video capture — device_path: {device_path}")
    try:
        video_capture = VideoCapture(config.parser)
    except BaseException as error:
        import traceback
        printer.print_msg(f"ERROR: Error initializing video capture: {type(error).__name__}: {error}")
        printer.print_msg(traceback.format_exc())
        sys.exit(1)
    printer.print_msg("Video capture initialized")
    return video_capture


def send_notification(target_gesture, printer):
    import pwd
    target_user = os.environ.get("SUDO_USER") or pwd.getpwuid(os.getuid())[0]
    script_path = "/usr/lib/howdy/dbus_notification.py"
    python_path = "/usr/lib/howdy/.venv/bin/python3"
    message = f"Gesture: {target_gesture}"

    try:
        subprocess.Popen(
            [
                "systemd-run", "--user", "-M", f"{target_user}@",
                python_path, script_path, "--message", message,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            close_fds=True,
            start_new_session=True,
        )
        time.sleep(0.1)
    except Exception:
        pass

    printer.print_msg(f"Sent notification to {target_user}: {target_gesture}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(12)

    user = sys.argv[1]
    printer = Printer()
    printer.print_msg("Starting compare.py")

    config = Config(printer).load()

    send_notification(config.target_gesture, printer)

    models, encodings = load_face_models(user, printer)
    face_detector, pose_predictor, face_encoder = init_face_detector(config, printer)
    video_capture = init_video_capture(config, printer)
    mp, recognizer = init_gesture_recognizer(printer)

    authenticator = Authenticator(
        config=config,
        user=user,
        printer=printer,
        models=models,
        encodings=encodings,
        face_detector=face_detector,
        pose_predictor=pose_predictor,
        face_encoder=face_encoder,
        video_capture=video_capture,
        mp=mp,
        recognizer=recognizer,
    )
    exit_code, match, match_index = authenticator.run()

    palm_pass_authenticator.finish(exit_code, match, match_index, authenticator, printer)
