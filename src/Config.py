import configparser

import paths_factory


class Config:
    def __init__(self, printer):
        self._printer = printer
        self.parser = configparser.ConfigParser()

        self.use_cnn = False
        self.timeout = 4
        self.dark_threshold = 50.0
        self.video_certainty = 0.35
        self.end_report = False
        self.save_failed = False
        self.save_successful = False
        self.gtk_stdout = False
        self.rotate = 0
        self.exposure = -1
        self.max_height = 320.0
        self.target_gesture = "rock"
        self.gesture_only = False

    def load(self):
        self._printer.print_msg("Reading configuration from disk")
        self.parser.read(paths_factory.config_file_path())
        self._printer.print_msg("Configuration loaded successfully")

        self.use_cnn = self.parser.getboolean("core", "use_cnn", fallback=False)
        self.timeout = self.parser.getint("video", "timeout", fallback=4)
        self.dark_threshold = self.parser.getfloat("video", "dark_threshold", fallback=50.0)
        self.video_certainty = self.parser.getfloat("video", "certainty", fallback=3.5) / 10
        self.end_report = self.parser.getboolean("debug", "end_report", fallback=False)
        self.save_failed = self.parser.getboolean("snapshots", "save_failed", fallback=False)
        self.save_successful = self.parser.getboolean("snapshots", "save_successful", fallback=False)
        self.gtk_stdout = self.parser.getboolean("debug", "gtk_stdout", fallback=False)
        self.rotate = self.parser.getint("video", "rotate", fallback=0)
        self.exposure = self.parser.getint("video", "exposure", fallback=-1)
        self.max_height = self.parser.getfloat("video", "max_height", fallback=320.0)
        self.target_gesture = self.parser.get("gestures", "target_gesture", fallback="rock")
        self.gesture_only = self.parser.getboolean("gesture-only", "gesture-only", fallback=False)

        self._printer.print_msg(f"Configuration gesture_only: {self.gesture_only}")
        return self.parser
