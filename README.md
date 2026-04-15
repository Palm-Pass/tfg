## Howdy gesture TFG

This repository contains a customized Howdy-based gesture authentication flow.

### Build and install on another PC

```bash
git clone https://github.com/Palm-Pass/tfg.git
cd tfg
makepkg -si
```

### Requirements

- Arch Linux or compatible system
- Python 3.10.19 available as `/usr/bin/python3.10`
- PAM and D-Bus installed

The package will create `/usr/lib/howdy-gesture/.venv` during installation and install the Python dependencies there.

### Notes

- `Makefile` is only for local development.
- The package source is the GitHub repository and its submodule `external/howdy`.
- If Python is not exactly 3.10.19, installation will fail by design.
