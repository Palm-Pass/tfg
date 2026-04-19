## Howdy gesture TFG

This repository contains a customized Howdy-based gesture authentication flow.

### Installation (Arch Linux)

```bash
git clone https://github.com/Palm-Pass/tfg.git
cd tfg
makepkg -f --noconfirm
sudo pacman -U ./howdy-gesture-tfg-*.pkg.tar.zst --noconfirm
```

### Requirements

- Arch Linux or compatible system
- Python 3.10+ available as `/usr/bin/python3`
- PAM and D-Bus installed
- Build tools: `meson`, `ninja`, `gcc`, `git`, `pkgconf`

The package installs standard Howdy layout (`/usr/lib/howdy`, `/etc/howdy`) and creates `/usr/lib/howdy/.venv` during installation to install Python dependencies.

### Post-install setup

1) Enable PAM for `sudo` (recommended first test target):

```bash
sudo cp /etc/pam.d/sudo /etc/pam.d/sudo.bak
sudoedit /etc/pam.d/sudo
```

Add this line at the top:

```pam
auth    sufficient    pam_howdy.so
```

2) Configure camera and timeout:

```bash
sudo howdy config
```

Recommended minimum values to start testing:

- `device_path = /dev/video0` (if black frames, try `/dev/video1`)
- `disabled = false`
- `timeout = 10`

3) Register face model and test:

```bash
sudo howdy -U $USER add
sudo howdy -U $USER test
```

4) Configure gesture mode:

```bash
howdy-gesture-config rock
howdy-gesture-only false
```

### Notes

- `Makefile` is only for local development.
- The package source is the GitHub repository and its submodule `external/howdy`.
- Installation uses Python 3.10+.
- If camera frames are black or too dark, verify `device_path` and camera availability (`/dev/video0`, `/dev/video1`).
