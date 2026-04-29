import atexit
import os
import pwd
import subprocess
import sys
import time

import cv2
import numpy as np
from howdy.i18n import _


class _AuthExit(Exception):
    def __init__(self, code, match=None, match_index=None):
        self.code = code
        self.match = match
        self.match_index = match_index


class Authenticator:
    def __init__(self, config, user, printer,
                 models, encodings,
                 face_detector, pose_predictor, face_encoder,
                 video_capture, mp, recognizer):
        self.config = config
        self.user = user
        self.printer = printer
        self.models = models
        self.encodings = encodings
        self.face_detector = face_detector
        self.pose_predictor = pose_predictor
        self.face_encoder = face_encoder
        self.video_capture = video_capture
        self.mp = mp
        self.recognizer = recognizer

        self.timings = {"st": time.time()}
        self.black_tries = 0
        self.dark_tries = 0
        self.frames = 0
        self.valid_frames = 0
        self.snapframes = []
        self.lowest_certainty = 10
        self.dark_running_total = 0
        self.clahe = None
        self.gtk_proc = None

        self.use_cnn = config.use_cnn
        self.timeout = config.timeout
        self.dark_threshold = config.dark_threshold
        self.video_certainty = config.video_certainty
        self.end_report = config.end_report
        self.save_failed = config.save_failed
        self.save_successful = config.save_successful
        self.gtk_stdout = config.gtk_stdout
        self.rotate = config.rotate
        self.exposure = config.exposure
        self.max_height = config.max_height
        self.target_gesture = config.target_gesture
        self.gesture_only = config.gesture_only

        height = self.video_capture.internal.get(cv2.CAP_PROP_FRAME_HEIGHT) or 1
        if self.rotate == 2:
            height = self.video_capture.internal.get(cv2.CAP_PROP_FRAME_WIDTH) or 1
        self.scaling_factor = (self.max_height / height) or 1

        self._start_ui()

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

    def _exit(self, code, match=None, match_index=None):
        raise _AuthExit(code, match, match_index)

    def send_to_ui(self, msg_type, message):
        if self.gtk_proc:
            message_formatted = msg_type + "=" + message + " \n"
            try:
                if self.gtk_proc.poll() is None:
                    self.gtk_proc.stdin.write(bytearray(message_formatted.encode("utf-8")))
                    self.gtk_proc.stdin.flush()
            except IOError:
                pass

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
            frame = cv2.resize(frame, None, fx=self.scaling_factor, fy=self.scaling_factor, interpolation=cv2.INTER_AREA)
            gsframe = cv2.resize(gsframe, None, fx=self.scaling_factor, fy=self.scaling_factor, interpolation=cv2.INTER_AREA)

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
            face_encoding = np.array(self.face_encoder.compute_face_descriptor(frame, face_landmark, 1))
            matches = np.linalg.norm(self.encodings - face_encoding, axis=1)
            match_index = np.argmin(matches)
            match = matches[match_index]

            if self.lowest_certainty > match:
                self.lowest_certainty = match

            if 0 < match < self.video_certainty:
                self.printer.print_msg(f"Confident match found: {match:.3f} < {self.video_certainty}")
                return True, match, match_index

            self.printer.print_msg(f"Match not confident enough: {match:.3f} >= {self.video_certainty}")

        return False, None, None

    def _process_gesture(self, frame):
        if self.mp is None or self.recognizer is None:
            return False

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=frame_rgb)
        recognition_result = self.recognizer.recognize(mp_image)

        detected_gesture = None
        if recognition_result.gestures:
            detected_gesture = recognition_result.gestures[0][0].category_name
            self.printer.print_msg(f"Detected gesture: {detected_gesture}, target: {self.target_gesture}")

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
                self.printer.print_msg("Failed due to timeout")
                if self.dark_tries == self.valid_frames:
                    print(_("All frames were too dark, please check dark_threshold in config"))
                    print(_("Average darkness: {avg}, Threshold: {threshold}").format(
                        avg=str(self.dark_running_total / max(1, self.valid_frames)),
                        threshold=str(self.dark_threshold),
                    ))
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
                self.printer.print_msg(f"Face match found! Certainty: {match:.3f}, Model index: {match_index}")
                self._exit(0, match, match_index)

            if not gesture_ok:
                self.printer.print_msg("Gesture did not match the target gesture.")

            if self.exposure != -1:
                self.video_capture.internal.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1.0)
                self.video_capture.internal.set(cv2.CAP_PROP_EXPOSURE, float(self.exposure))

    def run(self):
        self.printer.print_msg("Starting authentication process")
        self.send_to_ui("M", _("Starting up..."))
        self.timings["in"] = time.time() - self.timings["st"]
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

        try:
            self.authenticate()
        except _AuthExit as e:
            return e.code, e.match, e.match_index

        return 11, None, None

    def cleanup(self):
        if self.gtk_proc:
            self.gtk_proc.terminate()

    def _get_xauthority_path(self):
        user = os.environ.get("SUDO_USER") or pwd.getpwuid(os.getuid())[0]
        try:
            user_home = pwd.getpwnam(user).pw_dir
        except KeyError:
            user_home = os.path.expanduser("~")
        return os.path.join(user_home, ".Xauthority")
