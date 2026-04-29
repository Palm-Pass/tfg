import logging
import os
import sys
import syslog
import warnings


class Printer:
    def __init__(self):
        syslog.openlog(ident="TFG-LOG", logoption=syslog.LOG_PID, facility=syslog.LOG_USER)

    def print_msg(self, message: str):
        syslog.syslog(syslog.LOG_INFO, f"TFG-LOG: {message}")


def setup_runtime_environment():
    os.environ.setdefault("HOME", os.path.expanduser("~"))

    try:
        sys.stderr = open("/tmp/tfg_error.log", "a")
        sys.stdout = open("/tmp/tfg_output.log", "a")
    except Exception:
        pass

    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
    os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
    os.environ["TF_FORCE_GPU_ALLOW_GROWTH"] = "true"
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    os.environ["TF_CPP_MIN_VLOG_LEVEL"] = "3"
    os.environ["ABSL_MIN_LOG_LEVEL"] = "3"


def silence_warnings():
    warnings.filterwarnings("ignore")
    warnings.simplefilter("ignore", FutureWarning)
    warnings.simplefilter("ignore", DeprecationWarning)
    warnings.simplefilter("ignore", PendingDeprecationWarning)

    logging.getLogger("tensorflow").setLevel(logging.ERROR)
    logging.getLogger("keras").setLevel(logging.ERROR)
    logging.getLogger("mediapipe").setLevel(logging.ERROR)
    logging.getLogger("protobuf").setLevel(logging.ERROR)
    logging.getLogger("absl").setLevel(logging.ERROR)
    logging.getLogger("google").setLevel(logging.CRITICAL)
    logging.getLogger("google.api_core").setLevel(logging.CRITICAL)