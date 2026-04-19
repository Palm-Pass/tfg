CC = gcc
CFLAGS = -fPIC -fno-stack-protector -Wall
LDFLAGS = -x --shared
LIBS = -lpam
TARGET = src/pam_gesture.so
OBJ = src/pam_gesture.o
# PAM_SUDO_FILE = /etc/pam.d/sudo
# PAM_HOWDY_LINE = auth    sufficient    pam_howdy.so

.PHONY: all clean dev-install install

all: $(TARGET)

$(OBJ): src/pam_gesture.c
	$(CC) $(CFLAGS) -c $< -o $@

$(TARGET): $(OBJ)
	ld $(LDFLAGS) -o $@ $(OBJ) $(LIBS)

clean:
	rm -f $(OBJ) $(TARGET)

# JUST FOR DEVELOPMENT PURPOSES, NOT FOR PRODUCTION USE
dev-install: $(TARGET)
	sudo cp $(TARGET) /usr/lib/security/
	sudo chmod 755 /usr/lib/security/pam_gesture.so
	sudo chown root:root /usr/lib/security/pam_gesture.so

# Miantain compatibility
install:
	@echo "Use 'make dev-install' (only development). For real installation use PKGBUILD/makepkg."
	@false

# pam-enable-sudo:
# 	@echo "[pam] Enabling Howdy for sudo in $(PAM_SUDO_FILE)"
# 	@sudo test -f "$(PAM_SUDO_FILE)"
# 	@sudo cp -an "$(PAM_SUDO_FILE)" "$(PAM_SUDO_FILE).howdy-gesture.bak"
# 	@sudo sh -c 'grep -Fqx "$(PAM_HOWDY_LINE)" "$(PAM_SUDO_FILE)" || { tmp=$$(mktemp); printf "%s\n" "$(PAM_HOWDY_LINE)" > "$$tmp"; cat "$(PAM_SUDO_FILE)" >> "$$tmp"; cat "$$tmp" > "$(PAM_SUDO_FILE)"; rm -f "$$tmp"; }'
# 	@echo "[pam] Done. Backup: $(PAM_SUDO_FILE).howdy-gesture.bak"

# pam-disable-sudo:
# 	@echo "[pam] Disabling Howdy for sudo in $(PAM_SUDO_FILE)"
# 	@sudo test -f "$(PAM_SUDO_FILE)"
# 	@sudo sh -c 'tmp=$$(mktemp); grep -Fvx "$(PAM_HOWDY_LINE)" "$(PAM_SUDO_FILE)" > "$$tmp"; cat "$$tmp" > "$(PAM_SUDO_FILE)"; rm -f "$$tmp"'
# 	@echo "[pam] Done."

# pam-status-sudo:
# 	@echo "[pam] Checking $(PAM_SUDO_FILE)"
# 	@grep -nF "$(PAM_HOWDY_LINE)" "$(PAM_SUDO_FILE)" || echo "[pam] Howdy line not present"