import atexit
import asyncio
import json
import os
import pwd
import subprocess
import sys
import time
from datetime import datetime, timezone

import cv2
import dlib
import numpy as np
from howdy import paths_factory
from howdy import snapshot
from Config import Config
from howdy.i18n import _
from howdy.recorders.video_capture import VideoCapture

try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
except ImportError:
    mp = None
    python = None
    vision = None


class Authenticator:
    def __init__(self, printer):
        self.printer = printer

        if len(sys.argv) < 2:
            self._exit(12)

        self.user = sys.argv[1]
        self.printer.print_msg(f"Authenticating user: {self.user}")

        self.timings = {"st": time.time()}
        self.models = []
        self.encodings = []

        self.black_tries = 0
        self.dark_tries = 0
        self.frames = 0
        self.valid_frames = 0

        self.snapframes = []
        self.lowest_certainty = 10

        self.face_detector = None
        self.pose_predictor = None
        self.face_encoder = None
        self.video_capture = None

        self.scaling_factor = 1
        self.clahe = None
        self.dark_running_total = 0
        self.gtk_proc = None

        self.config_loader = Config(self.printer)
        self.config = self.config_loader.load()
        self._apply_config_values()
        self._start_ui()

    def _apply_config_values(self):
        self.use_cnn = self.config_loader.use_cnn
        self.timeout = self.config_loader.timeout
        self.dark_threshold = self.config_loader.dark_threshold
        self.video_certainty = self.config_loader.video_certainty
        self.end_report = self.config_loader.end_report
        self.save_failed = self.config_loader.save_failed
        self.save_successful = self.config_loader.save_successful
        self.gtk_stdout = self.config_loader.gtk_stdout
        self.rotate = self.config_loader.rotate
        self.exposure = self.config_loader.exposure
        self.max_height = self.config_loader.max_height
        self.target_gesture = self.config_loader.target_gesture
        self.gesture_only = self.config_loader.gesture_only

    def _start_ui(self):
        gtk_pipe = sys.stdout if self.gtk_stdout else subprocess.DEVNULL

        env = os.environ.copy()
        env["DISPLAY"] = ":0"
        env["XAUTHORITY"] = self._get_xauthority_path()

        try:
            self.gtk_proc = subprocess.Popen(
                ["howdy-gtk", "--start-auth-ui"],
                stdin=subprocess.PIPE,
                stdout=gtk_pipe,
                stderr=gtk_pipe,
                env=env,
            )
            atexit.register(self.cleanup)
        except FileNotFoundError:
            self.gtk_proc = None

    def _exit(self, code=None):
        if code is not None:
            sys.exit(code)

    def gesture_recognition_init(self):
        if python is None or vision is None:
            self.printer.print_msg("ERROR: MediaPipe is unavailable")
            return

        model_path = os.path.join("/usr/lib/howdy", "models/gesture_recognizer.task")
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.GestureRecognizerOptions(base_options=base_options)
        self.recognizer = vision.GestureRecognizer.create_from_options(options)
        self.gesture_names = ["rock", "paper", "scissors"]
        self.printer.print_msg(f"Target gesture: {self.target_gesture}")

    def send_to_ui(self, msg_type, message):
        if hasattr(self, "gtk_proc") and self.gtk_proc:
            message_formatted = msg_type + "=" + message + " \n"
            try:
                if self.gtk_proc.poll() is None:
                    self.gtk_proc.stdin.write(bytearray(message_formatted.encode("utf-8")))
                    self.gtk_proc.stdin.flush()
            except IOError:
                pass

    def init_detector(self):
        self.printer.print_msg("Initializing face detection models")

        if not os.path.isfile(paths_factory.shape_predictor_5_face_landmarks_path()):
            print(_("Data files have not been downloaded, please run the following commands:"))
            print("\n\tcd " + paths_factory.dlib_data_dir_path())
            print("\tsudo ./install.sh\n")
            self._exit(1)

        if self.use_cnn:
            self.printer.print_msg("Using CNN face detector")
            self.face_detector = dlib.cnn_face_detection_model_v1(
                paths_factory.mmod_human_face_detector_path()
            )
        else:
            self.printer.print_msg("Using HOG face detector")
            self.face_detector = dlib.get_frontal_face_detector()

        self.pose_predictor = dlib.shape_predictor(
            paths_factory.shape_predictor_5_face_landmarks_path()
        )
        self.face_encoder = dlib.face_recognition_model_v1(
            paths_factory.dlib_face_recognition_resnet_model_v1_path()
        )
        self.printer.print_msg("Face detection models initialized successfully")

    def make_snapshot(self, snapshot_type):
        snapshot.generate(
            self.snapframes,
            [
                snapshot_type + _(" LOGIN"),
                _("Date: ") + datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M:%S UTC"),
                _("Scan time: ") + str(round(time.time() - self.timings["fr"], 2)) + "s",
                _("Frames: ")
                + str(self.frames)
                + " ("
                + str(round(self.frames / (time.time() - self.timings["fr"]), 2))
                + "FPS)",
                _("Hostname: ") + os.uname().nodename,
                _("Best certainty value: ") + str(round(self.lowest_certainty * 10, 1)),
            ],
        )

    def load_models(self):
        self.printer.print_msg(f"Loading face models for user: {self.user}")
        try:
            self.models = json.load(open(paths_factory.user_model_path(self.user)))
            self.printer.print_msg(f"Loaded {len(self.models)} face model(s)")

            for model in self.models:
                self.encodings += model["data"]
        except FileNotFoundError:
            self._exit(10)

        if len(self.models) < 1:
            self._exit(10)

    def initialize_video_capture(self):
        self.printer.print_msg("Initializing video capture")
        self.timings["ic"] = time.time()

        try:
            self.video_capture = VideoCapture(self.config)
        except Exception as error:
            self.printer.print_msg(f"ERROR: Error initializing video capture: {error}")
            raise

        self.timings["ic"] = time.time() - self.timings["ic"]

        height = self.video_capture.internal.get(cv2.CAP_PROP_FRAME_HEIGHT) or 1
        if self.rotate == 2:
            height = self.video_capture.internal.get(cv2.CAP_PROP_FRAME_WIDTH) or 1

        self.scaling_factor = (self.max_height / height) or 1
        self.printer.print_msg(
            f"Video capture initialized. Resolution: {height}px, Scaling factor: {self.scaling_factor}"
        )

    def setup_processing(self):
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    def process_frame_darkness(self, gsframe):
        hist = cv2.calcHist([gsframe], [0], None, [8], [0, 256])
        hist_total = np.sum(hist)

        darkness = hist[0] / hist_total * 100

        if (hist_total == 0) or (darkness == 100):
            self.black_tries += 1
            return True, darkness

        self.dark_running_total += darkness
        self.valid_frames += 1

        if darkness > self.dark_threshold:
            self.dark_tries += 1
            return True, darkness

        return False, darkness

    def apply_frame_transformations(self, frame, gsframe):
        if self.scaling_factor != 1:
            frame = cv2.resize(
                frame,
                None,
                fx=self.scaling_factor,
                fy=self.scaling_factor,
                interpolation=cv2.INTER_AREA,
            )
            gsframe = cv2.resize(
                gsframe,
                None,
                fx=self.scaling_factor,
                fy=self.scaling_factor,
                interpolation=cv2.INTER_AREA,
            )

        if self.rotate == 1:
            if self.frames % 3 == 1:
                frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
                gsframe = cv2.rotate(gsframe, cv2.ROTATE_90_COUNTERCLOCKWISE)
            if self.frames % 3 == 2:
                frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                gsframe = cv2.rotate(gsframe, cv2.ROTATE_90_CLOCKWISE)
        elif self.rotate == 2:
            if self.frames % 2 == 0:
                frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
                gsframe = cv2.rotate(gsframe, cv2.ROTATE_90_COUNTERCLOCKWISE)
            else:
                frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                gsframe = cv2.rotate(gsframe, cv2.ROTATE_90_CLOCKWISE)

        return frame, gsframe

    def detect_and_match_faces(self, frame, gsframe):
        face_locations = self.face_detector(gsframe, 1)

        if len(face_locations) > 0:
            self.printer.print_msg(f"Detected {len(face_locations)} face(s) in frame")

        for face_location in face_locations:
            if self.use_cnn:
                face_location = face_location.rect

            face_landmark = self.pose_predictor(frame, face_location)
            face_encoding = np.array(
                self.face_encoder.compute_face_descriptor(frame, face_landmark, 1)
            )

            matches = np.linalg.norm(self.encodings - face_encoding, axis=1)

            match_index = np.argmin(matches)
            match = matches[match_index]

            if self.lowest_certainty > match:
                self.lowest_certainty = match

            if 0 < match < self.video_certainty:
                self.printer.print_msg(
                    f"Confident match found: {match:.3f} < {self.video_certainty}"
                )
                return True, match, match_index

            self.printer.print_msg(
                f"Match not confident enough: {match:.3f} >= {self.video_certainty}"
            )

        return False, None, None

    def handle_successful_authentication(self, match, match_index):
        self.printer.print_msg("Handling successful authentication")
        self.timings["tt"] = time.time() - self.timings["st"]
        self.timings["fl"] = time.time() - self.timings["fr"]

        if self.end_report:
            self._print_debug_report(match, match_index)

        if self.save_successful:
            self.make_snapshot(_("SUCCESSFUL"))

        if self.config.getboolean("rubberstamps", "enabled", fallback=False):
            self._execute_rubberstamps()

        self._exit(0)

    def _print_debug_report(self, match, match_index):
        def print_timing(label, key):
            print("  %s: %dms" % (label, round(self.timings[key] * 1000)))

        print(_("Time spent"))
        print_timing(_("Starting up"), "in")
        print(
            _("  Open cam + load libs: %dms")
            % (round(max(self.timings["ll"], self.timings["ic"]) * 1000))
        )
        print_timing(_("  Opening the camera"), "ic")
        print_timing(_("  Importing recognition libs"), "ll")
        print_timing(_("Searching for known face"), "fl")
        print_timing(_("Total time"), "tt")

        print(_("\nResolution"))
        width = self.video_capture.fw or 1
        height = self.video_capture.internal.get(cv2.CAP_PROP_FRAME_HEIGHT) or 1
        print(_("  Native: %dx%d") % (height, width))

        print(_("\nFrames searched: %d (%.2f fps)") % (self.frames, self.frames / self.timings["fl"]))
        print(_("Black frames ignored: %d ") % (self.black_tries,))
        print(_("Dark frames ignored: %d ") % (self.dark_tries,))
        print(_("Certainty of winning frame: %.3f") % (match * 10,))
        print(_('Winning model: %d ("%s")') % (match_index, self.models[match_index]["label"]))

    def _execute_rubberstamps(self):
        import rubberstamps

        self.send_to_ui("S", "")

        rubberstamps.execute(
            self.config,
            self.gtk_proc,
            {
                "video_capture": self.video_capture,
                "face_detector": self.face_detector,
                "pose_predictor": self.pose_predictor,
                "clahe": self.clahe,
            },
        )

    def _process_gesture(self, frame):
        if mp is None or not hasattr(self, "recognizer"):
            return False

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)

        recognition_result = self.recognizer.recognize(mp_image)

        detected_gesture = None
        if recognition_result.gestures:
            detected_gesture = recognition_result.gestures[0][0].category_name
            self.printer.print_msg(
                f"Detected gesture: {detected_gesture}, target gesture: {self.target_gesture}"
            )

        return detected_gesture == self.target_gesture

    def authenticate(self):
        self.printer.print_msg("Starting main authentication loop")
        self.send_to_ui("M", _("Identifying you..."))

        self.send_to_ui("M", f"The target gesture is: {self.target_gesture}.")
        self.printer.print_msg(f"The target gesture is: {self.target_gesture}.")
        time.sleep(5)

        self.timings["fr"] = time.time()

        while True:
            self.frames += 1

            if self.frames % 10 == 0:
                self.printer.print_msg(f"Tried {self.frames} frames")

            ui_subtext = "Scanned " + str(self.valid_frames - self.dark_tries) + " frames"
            if self.dark_tries > 1:
                ui_subtext += " (skipped " + str(self.dark_tries) + " dark frames)"
            self.send_to_ui("S", ui_subtext)

            if time.time() - self.timings["fr"] > self.timeout:
                if self.save_failed:
                    self.make_snapshot(_("FAILED"))

                self.printer.print_msg("Failed due to timeout")

                if self.dark_tries == self.valid_frames:
                    print(_("All frames were too dark, please check dark_threshold in config"))
                    print(
                        _("Average darkness: {avg}, Threshold: {threshold}").format(
                            avg=str(self.dark_running_total / max(1, self.valid_frames)),
                            threshold=str(self.dark_threshold),
                        )
                    )
                    self._exit(13)
                self._exit(11)

            frame, gsframe = self.video_capture.read_frame()
            gsframe = self.clahe.apply(gsframe)

            if self.save_failed or self.save_successful:
                if len(self.snapframes) < 3:
                    self.snapframes.append(frame)

            skip_frame, __ = self.process_frame_darkness(gsframe)
            if skip_frame:
                continue

            frame, gsframe = self.apply_frame_transformations(frame, gsframe)

            match_found, match, match_index = self.detect_and_match_faces(frame, gsframe)
            gesture_ok = self._process_gesture(frame)

            if (match_found or self.gesture_only) and gesture_ok:
                if self.gesture_only:
                    match = 0.0
                    match_index = 0
                self.printer.print_msg(
                    f"Face match found! Certainty: {match:.3f}, Model index: {match_index}"
                )
                self.handle_successful_authentication(match, match_index)

            if not gesture_ok:
                self.printer.print_msg("Gesture did not match the target gesture.")

            if self.exposure != -1:
                self.video_capture.internal.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1.0)
                self.video_capture.internal.set(cv2.CAP_PROP_EXPOSURE, float(self.exposure))

    def run(self):
        self.printer.print_msg("Starting authentication process")

        self.send_to_ui("M", _("Starting up..."))

        self.timings["in"] = time.time() - self.timings["st"]

        self.load_models()
        self.gesture_recognition_init()

        self.timings["ll"] = time.time()
        self.init_detector()
        self.timings["ll"] = time.time() - self.timings["ll"]

        self.initialize_video_capture()
        self.setup_processing()
        self.authenticate()

    def cleanup(self):
        if self.gtk_proc:
            self.gtk_proc.terminate()

    def _get_user(self):
        return os.environ.get("SUDO_USER") or pwd.getpwuid(os.getuid())[0]

    def _get_xauthority_path(self):
        user = self._get_user()

        try:
            user_home = pwd.getpwnam(user).pw_dir
        except KeyError:
            user_home = os.path.expanduser("~")

        return os.path.join(user_home, ".Xauthority")

    async def send_notification(self):
        target_user = self._get_user()
        base_path = os.path.dirname(os.path.abspath(__file__))
        binary_path = os.path.join(base_path, "dbus_notification")
        message = f"Gesto: {self.target_gesture}"

        try:
            subprocess.Popen(
                ["systemd-run", "--user", "-M", f"{target_user}@", binary_path, message],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                close_fds=True,
                start_new_session=True,
            )

            time.sleep(0.1)
        except Exception:
            pass

        self.printer.print_msg(
            f"Sent notification to user {target_user} with gesture {self.target_gesture}"
        )


async def run_authenticator(printer):
    authenticator = Authenticator(printer)
    await authenticator.send_notification()
    authenticator.run()
