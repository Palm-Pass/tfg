import sys
import time
from datetime import datetime, timezone

from howdy import snapshot
from howdy.i18n import _

import cv2


def finish(exit_code, match, match_index, auth, printer):
    if exit_code == 0:
        _handle_success(match, match_index, auth, printer)
    else:
        if auth.save_failed:
            _make_snapshot(_("FAILED"), auth)
        printer.print_msg(f"PAM authentication failed with code {exit_code}")
        sys.exit(exit_code)


def _handle_success(match, match_index, auth, printer):
    printer.print_msg("Authentication successful")
    auth.timings["tt"] = time.time() - auth.timings["st"]
    auth.timings["fl"] = time.time() - auth.timings["fr"]

    if auth.end_report:
        _print_debug_report(match, match_index, auth)

    if auth.save_successful:
        _make_snapshot(_("SUCCESSFUL"), auth)

    if auth.config.parser.getboolean("rubberstamps", "enabled", fallback=False):
        _execute_rubberstamps(auth)

    sys.exit(0)


def _make_snapshot(snapshot_type, auth):
    snapshot.generate(auth.snapframes, [
        snapshot_type + _(" LOGIN"),
        _("Date: ") + datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M:%S UTC"),
        _("Scan time: ") + str(round(time.time() - auth.timings["fr"], 2)) + "s",
        _("Frames: ") + str(auth.frames) + " ("
        + str(round(auth.frames / (time.time() - auth.timings["fr"]), 2)) + "FPS)",
        _("Hostname: ") + __import__("os").uname().nodename,
        _("Best certainty value: ") + str(round(auth.lowest_certainty * 10, 1)),
    ])


def _print_debug_report(match, match_index, auth):
    def print_timing(label, key):
        print("  %s: %dms" % (label, round(auth.timings[key] * 1000)))

    print(_("Time spent"))
    print_timing(_("Starting up"), "in")
    print(_("  Open cam + load libs: %dms") % (round(max(auth.timings["ll"], auth.timings["ic"]) * 1000)))
    print_timing(_("  Opening the camera"), "ic")
    print_timing(_("  Importing recognition libs"), "ll")
    print_timing(_("Searching for known face"), "fl")
    print_timing(_("Total time"), "tt")

    print(_("\nResolution"))
    width = auth.video_capture.fw or 1
    height = auth.video_capture.internal.get(cv2.CAP_PROP_FRAME_HEIGHT) or 1
    print(_("  Native: %dx%d") % (height, width))
    print(_("\nFrames searched: %d (%.2f fps)") % (auth.frames, auth.frames / auth.timings["fl"]))
    print(_("Black frames ignored: %d ") % (auth.black_tries,))
    print(_("Dark frames ignored: %d ") % (auth.dark_tries,))
    print(_("Certainty of winning frame: %.3f") % (match * 10,))
    print(_('Winning model: %d ("%s")') % (match_index, auth.models[match_index]["label"]))


def _execute_rubberstamps(auth):
    import rubberstamps
    auth.send_to_ui("S", "")
    rubberstamps.execute(auth.config.parser, auth.gtk_proc, {
        "video_capture": auth.video_capture,
        "face_detector": auth.face_detector,
        "pose_predictor": auth.pose_predictor,
        "clahe": auth.clahe,
    })
