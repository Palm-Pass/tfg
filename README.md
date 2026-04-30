## Howdy Gesture TFG

Face + gesture authentication layer for Linux PAM, built on top of [Howdy](https://github.com/boltgolt/howdy).

Authentication succeeds when the user's face is recognized **and** the correct hand gesture is detected simultaneously. Optionally, gesture-only mode can be enabled to skip face recognition.

---

### Requirements

- Arch Linux
- `uv` — Python package manager (`sudo pacman -S uv`)
- `gcc`, `git`, `cmake` — build tools (`sudo pacman -S gcc git cmake`)
- A compatible infrared or regular webcam

---

### Installation

```bash
git clone https://github.com/Palm-Pass/tfg.git
cd tfg
makepkg -si
```

`makepkg -si` builds the package, installs it via pacman, and runs the post-install hook which:
- Creates a Python virtual environment at `/usr/lib/howdy/.venv` and installs all dependencies via `uv`
- Downloads the required dlib face recognition models

---

### Post-install setup

#### 1. Configure the camera

```bash
sudo howdy config
```

Set at minimum:

```ini
[video]
device_path = /dev/video2   # adjust to your camera device
timeout = 10
```

To find your camera device:

```bash
ls /dev/video*
```

If frames are too dark or black, try a different device path (`/dev/video0`, `/dev/video1`, etc.) or reduce the `dark_threshold` value.

#### 2. Add your face model

```bash
sudo howdy -U $USER add
```

Verify it works:

```bash
sudo howdy -U $USER test
```

#### 3. Configure the target gesture

```bash
sudo howdy-gesture-config rock   # available: rock, paper, scissors
```

#### 4. Enable PAM authentication

Add `pam_gesture.so` to the relevant PAM config file. The line must go **at the top** of the `auth` block.

**For `sudo`:**

```bash
sudo cp /etc/pam.d/sudo /etc/pam.d/sudo.bak
sudo nano /etc/pam.d/sudo
```

**For login (display manager / TTY):**

```bash
sudo cp /etc/pam.d/system-auth /etc/pam.d/system-auth.bak
sudo nano /etc/pam.d/system-auth
```

In both cases, add this line at the top:

```
auth    sufficient    pam_gesture.so
```

> **Note:** Modifying `system-auth` affects all PAM-aware services that include it (login, screen lock, su, etc.). Always keep a backup and a root shell open while testing.

---

### Usage

Once PAM is configured, authentication is automatic when running `sudo` or any PAM-protected action:

1. A desktop notification appears showing the gesture to perform (requires a notification daemon)
2. Look at the camera and perform the gesture
3. Authentication succeeds when your face is recognized and the gesture matches

#### Gesture-only mode

To authenticate using only the gesture (no face recognition required):

```bash
sudo howdy-gesture-only true
```

To re-enable combined face + gesture authentication:

```bash
sudo howdy-gesture-only false
```

---

### Troubleshooting

**Authentication fails instantly**
- Check the camera device path: `ls /dev/video*`
- Verify the config: `sudo howdy config` → `device_path`
- Check logs: `journalctl -xe | grep TFG-LOG`

**Face not recognized**
- Re-add your face model: `sudo howdy -U $USER add`
- Increase `timeout` in the config to give more time

**AVX2 / SIGILL error (virtual machines)**
- MediaPipe requires AVX2 CPU instructions. In VMs without AVX2, gesture recognition is automatically disabled and authentication falls back to face-only mode.
