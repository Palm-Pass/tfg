#!/usr/bin/env python3

# Compare incoming video with known faces  
# Running in a local python instance to get around PATH issues

# Import time so we can start timing asap
from random import random
import time

# Import required modules
import sys
import os
import syslog

# SUPPRESS STDERR/STDOUT IMMEDIATELY at the file descriptor level
# This catches C++ library warnings that are written before Python imports complete
devnull = os.open(os.devnull, os.O_WRONLY)
os.dup2(devnull, 2)  # Redirect fd 2 (stderr) to /dev/null
os.dup2(devnull, 1)  # Redirect fd 1 (stdout) to /dev/null

# Configure environment variables BEFORE importing heavy libraries
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress TensorFlow C++ logs
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'  # Disable oneDNN optimization warnings
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'  # Force CPU only (no GPU warnings)
os.environ['TF_CPP_MIN_VLOG_LEVEL'] = '3'
os.environ['ABSL_MIN_LOG_LEVEL'] = '3'  # Suppress ABSL warnings

def silence_warnings():
    """Suppress various warnings from libraries like TensorFlow, MediaPipe, etc."""
    import warnings
    import logging
    
    # Suppress all Python warnings
    warnings.filterwarnings('ignore')
    warnings.simplefilter('ignore', FutureWarning)
    warnings.simplefilter('ignore', DeprecationWarning)
    warnings.simplefilter('ignore', PendingDeprecationWarning)
    
    # Configure logging to suppress library warnings
    logging.getLogger('tensorflow').setLevel(logging.ERROR)
    logging.getLogger('keras').setLevel(logging.ERROR)
    logging.getLogger('mediapipe').setLevel(logging.ERROR)
    logging.getLogger('protobuf').setLevel(logging.ERROR)
    logging.getLogger('absl').setLevel(logging.ERROR)
    logging.getLogger('google').setLevel(logging.CRITICAL)
    logging.getLogger('google.api_core').setLevel(logging.CRITICAL)
    
    # Restore stderr and stdout for Python logging
    sys.stderr = os.fdopen(os.dup(2), 'w')
    sys.stdout = os.fdopen(os.dup(1), 'w')
    
    # Try to suppress TensorFlow specifically if available
    try:
        import tensorflow as tf
        tf.get_logger().setLevel(logging.ERROR)
    except ImportError:
        pass

# Call silence_warnings BEFORE any heavy imports
silence_warnings()

syslog.openlog(ident="TFG-LOG", logoption=syslog.LOG_PID, facility=syslog.LOG_USER)

def print_msg(message: str):
    """Log message to syslog"""
    syslog.syslog(syslog.LOG_INFO, f"TFG-LOG: {message}")

sys.path.append("/usr/lib/howdy")
import json
import configparser
import dlib
import cv2
from datetime import timezone, datetime
import warnings
import atexit
import subprocess
import snapshot
import numpy as np
import paths_factory
from recorders.video_capture import VideoCapture
from i18n import _
import subprocess
import pwd
import asyncio
try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    import random as rnd
except ImportError as e:
    print_msg(f"ERROR: Error loading mediapipe: {e}")


def exit(code=None):
    """Exit while closing howdy-gtk properly"""
    # Exit compare
    if code is not None:
        sys.exit(code)


print_msg("Message from TFG Project")
print_msg("Loaded uv libraries correctly")

#TODO: Monkey patch howdy paths

#TODO: Create pam .so file so it launches my compare.py and not howdy
class Authenticator:
    """Face authentication class for Howdy"""

    def __init__(self):
        print_msg("Initializing Authenticator class")
        # Make sure we were given an username to test against
        if len(sys.argv) < 2:
            exit(12)

        # The username of the user being authenticated
        self.user = sys.argv[1]
        print_msg(f"Authenticating user: {self.user}")
        
        # Initialize timings
        self.timings = {"st": time.time()}
        
        # Load config settings
        self.config = self._read_config()
        
        # The model file contents
        self.models = []
        # Encoded face models
        self.encodings = []
        
        # Frame counters
        self.black_tries = 0
        self.dark_tries = 0
        self.frames = 0
        self.valid_frames = 0
        
        # Captured frames for snapshot capture
        self.snapframes = []
        # Tracks the lowest certainty value in the loop
        self.lowest_certainty = 10
        
        # Face recognition/detection instances
        self.face_detector = None
        self.pose_predictor = None
        self.face_encoder = None
        
        # Video capture instance
        self.video_capture = None
        
        # Other processing variables
        self.scaling_factor = 1
        self.clahe = None
        self.dark_running_total = 0
        
        # UI process
        self.gtk_proc = None

        #Gesture only needed for testing
        self.only_gesture = False
    #TODO: Eliminate name from path, form first line, from config.ini and from howdy/compare.py   
    def gesture_recognition_init(self):
        user = self._get_user()
        base_options = python.BaseOptions(model_asset_path=f'/home/{user}/Escritorio/tfg/notebooks/rock_exported_model/gesture_recognizer.task')
        options = vision.GestureRecognizerOptions(base_options=base_options)
        self.recognizer = vision.GestureRecognizer.create_from_options(options)
        self.gesture_names = ["rock", "paper", "scissors"]
        print_msg(f"Target gesture: {self.target_gesture}")
        
    
    def send_to_ui(self, msg_type, message):
        """Send message to the auth ui"""
        # Only execute if the process started
        if hasattr(self, 'gtk_proc') and self.gtk_proc:
            # Format message so the ui can parse it
            message_formatted = msg_type + "=" + message + " \n"

            # Try to send the message to the auth ui, but it's okay if that fails
            try:
                if self.gtk_proc.poll() is None:  # Make sure the gtk_proc is still running
                    self.gtk_proc.stdin.write(bytearray(message_formatted.encode("utf-8")))
                    self.gtk_proc.stdin.flush()
            except IOError:
                pass

    def init_detector(self):
        """Initialize face detector, encoder and predictor"""
        print_msg("Initializing face detection models")
        # Test if at least 1 of the data files is there and abort if it's not
        if not os.path.isfile(paths_factory.shape_predictor_5_face_landmarks_path()):
            print(_("Data files have not been downloaded, please run the following commands:"))
            print("\n\tcd " + paths_factory.dlib_data_dir_path())
            print("\tsudo ./install.sh\n")
            exit(1)

        # Use the CNN detector if enabled
        if self.use_cnn:
            print_msg("Using CNN face detector")
            self.face_detector = dlib.cnn_face_detection_model_v1(
                paths_factory.mmod_human_face_detector_path()
            )
        else:
            print_msg("Using HOG face detector")
            self.face_detector = dlib.get_frontal_face_detector()

        # Start the others regardless
        self.pose_predictor = dlib.shape_predictor(
            paths_factory.shape_predictor_5_face_landmarks_path()
        )
        self.face_encoder = dlib.face_recognition_model_v1(
            paths_factory.dlib_face_recognition_resnet_model_v1_path()
        )
        print_msg("Face detection models initialized successfully")

    def make_snapshot(self, snapshot_type):
        """Generate snapshot after detection"""
        snapshot.generate(
            self.snapframes,
            [
                snapshot_type + _(" LOGIN"),
                _("Date: ") + datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M:%S UTC"),
                _("Scan time: ") + str(round(time.time() - self.timings["fr"], 2)) + "s",
                _("Frames: ") + str(self.frames) + " (" + str(round(self.frames / (time.time() - self.timings["fr"]), 2)) + "FPS)",
                _("Hostname: ") + os.uname().nodename,
                _("Best certainty value: ") + str(round(self.lowest_certainty * 10, 1)),
            ],
        )

    def load_models(self):
        """Load face models from disk"""
        print_msg(f"Loading face models for user: {self.user}")
        try:
            self.models = json.load(open(paths_factory.user_model_path(self.user)))
            print_msg(f"Loaded {len(self.models)} face model(s)")

            for model in self.models:
                self.encodings += model["data"]
        except FileNotFoundError:
            exit(10)

        # Check if the file contains a model
        if len(self.models) < 1:
            exit(10)

    def _read_config(self):
        """Read configuration from disk and initialize UI process"""
        print_msg("Reading configuration from disk")
        config = configparser.ConfigParser()
        config.read(paths_factory.config_file_path())
        print_msg("Configuration loaded successfully")

        # Get all config values needed
        self.use_cnn = config.getboolean("core", "use_cnn", fallback=False)
        self.timeout = config.getint("video", "timeout", fallback=4)
        self.dark_threshold = config.getfloat("video", "dark_threshold", fallback=50.0)
        self.video_certainty = config.getfloat("video", "certainty", fallback=3.5) / 10
        self.end_report = config.getboolean("debug", "end_report", fallback=False)
        self.save_failed = config.getboolean("snapshots", "save_failed", fallback=False)
        self.save_successful = config.getboolean("snapshots", "save_successful", fallback=False)
        self.gtk_stdout = config.getboolean("debug", "gtk_stdout", fallback=False)
        self.rotate = config.getint("video", "rotate", fallback=0)
        self.exposure = config.getint("video", "exposure", fallback=-1)
        self.max_height = config.getfloat("video", "max_height", fallback=320.0)
        self.target_gesture = config.get("gestures", "target_gesture", fallback="rock")
        # Send the gtk output to the terminal if enabled in the config
        gtk_pipe = sys.stdout if self.gtk_stdout else subprocess.DEVNULL
        
        self.gesture_only = config.getboolean("gesture-only", "gesture-only", fallback=False)

        print_msg(f"Configuration gesture_only: {self.gesture_only}")

        env = os.environ.copy()
        env["DISPLAY"] = ":0"  
        env["XAUTHORITY"] = f"/home/{os.getlogin()}/.Xauthority"
        # Ensure the GTK UI can find the display
        # Start the auth ui, register it to be always be closed on exit
        try:
            self.gtk_proc = subprocess.Popen(
                ["howdy-gtk", "--start-auth-ui"],
                stdin=subprocess.PIPE,
                stdout=gtk_pipe,
                stderr=gtk_pipe,
                env=env
            )
            atexit.register(self.cleanup)
        except FileNotFoundError:
            pass

        return config

    def initialize_video_capture(self):
        """Initialize video capture and calculate scaling factor"""
        print_msg("Initializing video capture")
        # Start video capture on the IR camera
        self.timings["ic"] = time.time()
        
        try:
            self.video_capture = VideoCapture(self.config)
        except Exception as e:
            print_msg(f"ERROR: Error initializing video capture: {e}")

        
        # Note the time it took to open the camera
        self.timings["ic"] = time.time() - self.timings["ic"]
        
        # Get the height of the image (which would be the width if screen is portrait oriented)
        height = self.video_capture.internal.get(cv2.CAP_PROP_FRAME_HEIGHT) or 1
        if self.rotate == 2:
            height = self.video_capture.internal.get(cv2.CAP_PROP_FRAME_WIDTH) or 1
            
        # Calculate the amount the image has to shrink
        self.scaling_factor = (self.max_height / height) or 1
        print_msg(f"Video capture initialized. Resolution: {height}px, Scaling factor: {self.scaling_factor}")

    def setup_processing(self):
        """Setup image processing components"""
        # Initiate histogram equalization
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    def process_frame_darkness(self, gsframe):
        """Check if frame is too dark and should be skipped"""
        # Create a histogram of the image with 8 values
        hist = cv2.calcHist([gsframe], [0], None, [8], [0, 256])
        # All values combined for percentage calculation
        hist_total = np.sum(hist)

        # Calculate frame darkness
        darkness = hist[0] / hist_total * 100

        # If the image is fully black due to a bad camera read, skip to the next frame
        if (hist_total == 0) or (darkness == 100):
            self.black_tries += 1
            return True, darkness

        self.dark_running_total += darkness
        self.valid_frames += 1

        # If the image exceeds darkness threshold due to subject distance, skip to the next frame
        if darkness > self.dark_threshold:
            self.dark_tries += 1
            return True, darkness
            
        return False, darkness

    def apply_frame_transformations(self, frame, gsframe):
        """Apply scaling and rotation transformations to frames"""
        # If the height is too high
        if self.scaling_factor != 1:
            # Apply that factor to the frame
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

        # Apply rotation based on configuration
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
        """Detect faces in frame and match against known encodings"""
        # Get all faces from that frame as encodings (Upsamples 1 time)
        face_locations = self.face_detector(gsframe, 1)
        
        if len(face_locations) > 0:
            print_msg(f"Detected {len(face_locations)} face(s) in frame")
        
        # Loop through each face
        for fl in face_locations:
            if self.use_cnn:
                fl = fl.rect

            # Fetch the faces in the image
            face_landmark = self.pose_predictor(frame, fl)
            face_encoding = np.array(
                self.face_encoder.compute_face_descriptor(frame, face_landmark, 1)
            )

            # Match this found face against a known face
            matches = np.linalg.norm(self.encodings - face_encoding, axis=1)

            # Get best match
            match_index = np.argmin(matches)
            match = matches[match_index]

            # Update certainty if we have a new low
            if self.lowest_certainty > match:
                self.lowest_certainty = match

            # Check if a match that's confident enough
            if 0 < match < self.video_certainty:
                print_msg(f"Confident match found: {match:.3f} < {self.video_certainty}")
                return True, match, match_index
            else:
                print_msg(f"Match not confident enough: {match:.3f} >= {self.video_certainty}")
                
        return False, None, None

    def handle_successful_authentication(self, match, match_index):
        """Handle successful authentication with reporting and cleanup"""
        print_msg("Handling successful authentication")
        self.timings["tt"] = time.time() - self.timings["st"]
        self.timings["fl"] = time.time() - self.timings["fr"]

        # If set to true in the config, print debug text
        if self.end_report:
            self._print_debug_report(match, match_index)

        # Make snapshot if enabled
        if self.save_successful:
            self.make_snapshot(_("SUCCESSFUL"))

        # Run rubberstamps if enabled
        if self.config.getboolean("rubberstamps", "enabled", fallback=False):
            self._execute_rubberstamps()

        # End peacefully
        exit(0)

    def _print_debug_report(self, match, match_index):
        """Print detailed debug information"""
        def print_timing(label, k):
            """Helper function to print a timing from the list"""
            print("  %s: %dms" % (label, round(self.timings[k] * 1000)))

        # Print a nice timing report
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
        
        # Show the total number of frames and calculate the FPS
        print(_("\nFrames searched: %d (%.2f fps)") % (self.frames, self.frames / self.timings["fl"]))
        print(_("Black frames ignored: %d ") % (self.black_tries,))
        print(_("Dark frames ignored: %d ") % (self.dark_tries,))
        print(_("Certainty of winning frame: %.3f") % (match * 10,))
        print(_('Winning model: %d ("%s")') % (match_index, self.models[match_index]["label"]))

    def _execute_rubberstamps(self):
        """Execute rubberstamps if enabled"""
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
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
    
	
        recognition_result = self.recognizer.recognize(mp_image)
	
        detected_gesture = None
        if recognition_result.gestures:
            # Cogemos el gesto con más confianza
            detected_gesture = recognition_result.gestures[0][0].category_name
            print_msg(f"Detected gesture: {detected_gesture}, target gesture: {self.target_gesture}")
        return detected_gesture == self.target_gesture


    def authenticate(self):
        """Main authentication loop"""
        print_msg("Starting main authentication loop")
        # Let the ui know that we're ready
        self.send_to_ui("M", _("Identifying you..."))

        # Start the read loop
        self.timings["fr"] = time.time()
        self.send_to_ui("M", f"The target gesture is: {self.target_gesture}.")
        print_msg(f"The target gesture is: {self.target_gesture}.")
        time.sleep(5)

        while True:
            # Increment the frame count every loop
            self.frames += 1

            if self.frames % 10 == 0:
                print_msg(f"Tried {self.frames} frames")

            # Form a string to let the user know we're real busy
            ui_subtext = "Scanned " + str(self.valid_frames - self.dark_tries) + " frames"
            if self.dark_tries > 1:
                ui_subtext += " (skipped " + str(self.dark_tries) + " dark frames)"
            # Show it in the ui as subtext
            self.send_to_ui("S", ui_subtext)

            # Stop if we've exceeded the time limit
            if time.time() - self.timings["fr"] > self.timeout:
                # Create a timeout snapshot if enabled
                if self.save_failed:
                    self.make_snapshot(_("FAILED"))

                print_msg("Failed due to timeout")

                if self.dark_tries == self.valid_frames:
                    print(_("All frames were too dark, please check dark_threshold in config"))
                    print(
                        _("Average darkness: {avg}, Threshold: {threshold}").format(
                            avg=str(self.dark_running_total / max(1, self.valid_frames)),
                            threshold=str(self.dark_threshold),
                        )
                    )
                    exit(13)
                else:
                    exit(11)

            # Grab a single frame of video
            frame, gsframe = self.video_capture.read_frame()
            gsframe = self.clahe.apply(gsframe)

            # If snapshots have been turned on
            if self.save_failed or self.save_successful:
                # Start capturing frames for the snapshot
                if len(self.snapframes) < 3:
                    self.snapframes.append(frame)

            # Check if frame is too dark
            skip_frame, darkness = self.process_frame_darkness(gsframe)
            if skip_frame:
                continue

            # Apply transformations to frames
            frame, gsframe = self.apply_frame_transformations(frame, gsframe)

            # Detect and match faces
            match_found, match, match_index = self.detect_and_match_faces(frame, gsframe)
            
            gesture_ok = self._process_gesture(frame)

            if (match_found or self.gesture_only) and gesture_ok:
                #Needed to handle a successful authentication when only gesture is enabled, otherwise match and match_index would be None
                if self.gesture_only:
                    match = 0.0
                    match_index = 0
                print_msg(f"Face match found! Certainty: {match:.3f}, Model index: {match_index}")
                self.handle_successful_authentication(match, match_index)

            if not gesture_ok:
                print_msg("Gesture did not match the target gesture.")

            # Set manual exposure if configured
            if self.exposure != -1:
                # For a strange reason on some cameras setting manual exposure works only after a couple frames
                # are captured and even after a delay it does not always work. Setting exposure at every frame is reliable though.
                self.video_capture.internal.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1.0)  # 1 = Manual
                self.video_capture.internal.set(cv2.CAP_PROP_EXPOSURE, float(self.exposure))

    def run(self):
        """Main execution method"""
        print_msg("Starting authentication process")
        
        # Write to the stdin to redraw ui
        self.send_to_ui("M", _("Starting up..."))

        # Save the time needed to start the script
        self.timings["in"] = time.time() - self.timings["st"]

        # Load face models
        self.load_models()

        self.gesture_recognition_init()

        # Import face recognition, takes some time
        self.timings["ll"] = time.time()
        
        # Initialize face detection
        self.init_detector()
        
        # Note the time it took to initialize detectors
        self.timings["ll"] = time.time() - self.timings["ll"]

        # Initialize video capture
        self.initialize_video_capture()
        
        # Setup image processing
        self.setup_processing()

        # Start authentication loop
        self.authenticate()


    def cleanup(self):
        if self.gtk_proc:
            self.gtk_proc.terminate()

    def _get_user(self): 
        return os.environ.get("SUDO_USER") or os.getlogin()
    
    async def send_notification(self):
        target_user = self._get_user()
        base_path = os.path.dirname(os.path.abspath(__file__))
        binary_path = os.path.join(base_path, "dbus_notification")
        msg = f"Gesto: {self.target_gesture}"

        try:
            subprocess.Popen(
                ["systemd-run", "--user", "-M", f"{target_user}@", binary_path, msg],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                close_fds=True,      
                start_new_session=True
            )

            time.sleep(0.1) 
        except Exception:
            pass

        print_msg(f"Sent notification to user {target_user} with gesture {self.target_gesture}")
if __name__ == "__main__":
    print_msg("Starting compare.py")
    authenticator = Authenticator()
    asyncio.run(authenticator.send_notification())
    authenticator.run()
