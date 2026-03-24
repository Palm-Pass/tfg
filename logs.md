# TFG Development Log

## Overall objective
This document summarizes the roadmap followed to integrate gesture detection into the Howdy authentication flow, including testing, refactoring, and PAM integration.

---

## 03/03/2026
### Initial environment
- Installed an Arch Linux virtual machine.
- Ran initial Howdy tests successfully.

## 04/03/2026
### Initial integration with PAM and repository
- Created the project repository.
- Redirected Howdy to use a custom `compare.py`.
- Verified PAM logs using `journalctl`.

### Applied changes
- Modified `/etc/pam.d/sudo`, adding at the top:
	- `auth sufficient pam_howdy.so`
- Adapted `/usr/lib/howdy/compare.py` to load the project script (PAM did not execute directly from `/home`), using:
	- `sys.path.insert(0, "/home/Escritorio/tfg/src")`
- Set execution permissions with `chmod +x` on the project directory.
- Replaced `print()` with `syslog.LOG_INFO` logs, since PAM has no standard output.

### Dependencies
- Created a `uv` environment in the desktop project.
- Added the virtual environment path to the Howdy bridge script.

## 05/03/2026
### Observability and flow understanding
- Added logical logs in Howdy's `compare.py` to identify which modules were running and when.
- Adjusted `compare.py` to better fit the project and improve code understanding.

## 09/03/2026
### Gesture model and refactoring
- Tested MediaPipe Model Maker.
- Updated project versions due to incompatibilities with `mediapipe-model-maker`.
- Ran the first notebook experiments on a rock-paper-scissors dataset.
- Refactored `compare.py` (reducing spaghetti code).
- Created the `Authenticator` class to better separate pipeline modules.

## 10/03/2026
### Gesture detection logic consolidation
- Finished the refactor.
- Added debug logs to `syslog` to validate that the pipeline flow remained correct after changes.
- Started and finished implementing gesture detection logic using the model trained in the notebook.

## 11/03/2026
### Howdy dependencies and validation
- Installed additional Howdy dependencies in the repository, since the bridge script moved to execution via `exec`.
- Located and used the `PKGBUILD` in `.cache/yay/howdy` to complete installation.
- Verified that gesture detection was working correctly.

## 14/03/2026
### User configuration improvement
- Identified a usability improvement: allow users to choose the key gesture more easily.
- Modified `/etc/howdy/config.ini` to support this configuration.

## 18/03/2026
### Preset-based gesture configuration
- Added file/configuration to select the gesture from model presets.
- Goal: avoid requiring users to edit `config.ini` manually.

## 19/03/2026
### Integration status
- Gesture configuration logic added and working correctly.

## 20/03/2026
### Notifications
- Tested popup notifications with PyGObject.
- Discarded due to limitations when launching under `sudo`.
- Adopted solution: use `subprocess` with the required permissions.

## 21/03/2026
### Final status of this phase
- Gesture configuration and detection logic working stably.
